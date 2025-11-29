"""Board monitoring and change detection logic."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class BoardState:
    """Represents the state of a TaskCards board at a point in time."""

    def __init__(self, data: dict[str, Any]):
        """
        Initialize board state from raw board data.

        Args:
            data: Raw board data from TaskCards (from Vuex store)
        """
        self.timestamp = datetime.now().isoformat()
        self.raw_data = data
        self.cards = self._extract_cards(data)

    def _extract_cards(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract card information from board data.

        Args:
            data: Raw board data

        Returns:
            Dictionary mapping card ID to card info (title, description)
        """
        cards = {}

        if "cards" in data:
            for card in data["cards"]:
                card_id = card.get("id")
                if card_id:
                    cards[card_id] = {
                        "title": card.get("title", ""),
                        "description": card.get("description", ""),
                    }

        return cards

    def to_dict(self) -> dict[str, Any]:
        """Convert board state to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "cards": self.cards,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardState":
        """Create BoardState from serialized dictionary."""
        state = cls.__new__(cls)
        state.timestamp = data["timestamp"]
        state.cards = data["cards"]
        state.raw_data = {}
        return state


class BoardMonitor:
    """Monitors a TaskCards board for changes."""

    def __init__(self, board_id: str, state_dir: Path | None = None):
        """
        Initialize the board monitor.

        Args:
            board_id: The board ID to monitor
            state_dir: Directory to store state files (defaults to ~/.cache/taskcards-monitor/)
        """
        self.board_id = board_id

        if state_dir is None:
            state_dir = Path.home() / ".cache" / "taskcards-monitor"

        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / f"{board_id}.json"

    def get_previous_state(self) -> BoardState | None:
        """
        Load the previously saved state.

        Returns:
            BoardState if exists, None otherwise
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file) as f:
                data = json.load(f)
                return BoardState.from_dict(data)
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def save_state(self, state: BoardState) -> None:
        """
        Save the current board state.

        Args:
            state: BoardState to save
        """
        with open(self.state_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def detect_changes(self, current: BoardState, previous: BoardState | None) -> dict[str, Any]:
        """
        Detect changes between current and previous board states.

        Only tracks:
        - Cards added (new card IDs)
        - Cards removed (missing card IDs)
        - Cards changed (same ID, different title or description)

        Args:
            current: Current board state
            previous: Previous board state (None on first run)

        Returns:
            Dictionary containing detected changes
        """
        if previous is None:
            return {
                "is_first_run": True,
                "cards_count": len(current.cards),
            }

        changes = {
            "is_first_run": False,
            "cards_added": [],
            "cards_removed": [],
            "cards_changed": [],
        }

        prev_ids = set(previous.cards.keys())
        curr_ids = set(current.cards.keys())

        # Cards added
        for card_id in curr_ids - prev_ids:
            card_data = current.cards[card_id]
            changes["cards_added"].append(
                {
                    "id": card_id,
                    "title": card_data["title"],
                    "description": card_data["description"],
                }
            )

        # Cards removed
        for card_id in prev_ids - curr_ids:
            card_data = previous.cards[card_id]
            changes["cards_removed"].append(
                {
                    "id": card_id,
                    "title": card_data["title"],
                    "description": card_data["description"],
                }
            )

        # Cards changed (same ID, different content)
        for card_id in prev_ids & curr_ids:
            prev_card = previous.cards[card_id]
            curr_card = current.cards[card_id]

            if (
                prev_card["title"] != curr_card["title"]
                or prev_card["description"] != curr_card["description"]
            ):
                changes["cards_changed"].append(
                    {
                        "id": card_id,
                        "old_title": prev_card["title"],
                        "new_title": curr_card["title"],
                        "old_description": prev_card["description"],
                        "new_description": curr_card["description"],
                    }
                )

        return changes
