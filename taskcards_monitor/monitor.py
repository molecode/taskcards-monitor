"""Board monitoring and change detection logic."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BoardState:
    """Represents the state of a TaskCards board at a point in time."""

    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    _board_data: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        """Store the full board data."""
        # Store the complete board data from the GraphQL response
        # The fetcher returns the board object directly
        self._board_data = self.data

    @property
    def cards(self) -> dict[str, dict[str, str]]:
        """
        Get cards in simplified format for display compatibility.

        Returns dict of {card_id: {"title": str, "description": str}}
        This maintains backward compatibility with existing display code.
        """
        cards_dict = {}
        cards_list = self._board_data.get("cards", [])

        for card in cards_list:
            card_id = card.get("id")
            if card_id:
                cards_dict[card_id] = {
                    "title": card.get("title", ""),
                    "description": card.get("description", ""),
                }

        return cards_dict

    @property
    def lists(self) -> list[dict[str, Any]]:
        """Get all lists from the board."""
        return self._board_data.get("lists", [])

    @property
    def board_name(self) -> str:
        """Get the board name."""
        return self._board_data.get("name", "")

    @property
    def board_description(self) -> str:
        """Get the board description."""
        return self._board_data.get("description", "")

    def get_card(self, card_id: str) -> dict[str, Any] | None:
        """
        Get full card data by ID.

        Returns complete card object with all fields including kanbanPosition.
        """
        for card in self._board_data.get("cards", []):
            if card.get("id") == card_id:
                return card
        return None

    def get_list(self, list_id: str) -> dict[str, Any] | None:
        """Get list data by ID."""
        for lst in self._board_data.get("lists", []):
            if lst.get("id") == list_id:
                return lst
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert board state to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "board": self._board_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardState":
        """Create BoardState from serialized dictionary."""
        state = object.__new__(cls)
        state.timestamp = data["timestamp"]
        state._board_data = data["board"]
        state.data = {}
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

        Args:
            current: Current board state
            previous: Previous board state (None if first run)

        Returns:
            Dictionary containing detected changes
        """
        current_cards = current.cards
        previous_cards = previous.cards if previous else {}

        if previous is None:
            return {
                "is_first_run": True,
                "cards_count": len(current_cards),
                "cards_added": [],
                "cards_removed": [],
                "cards_changed": [],
            }

        # Cards added/removed
        added_ids = set(current_cards) - set(previous_cards)
        removed_ids = set(previous_cards) - set(current_cards)
        common_ids = set(current_cards) & set(previous_cards)

        cards_added = [
            {
                "id": card_id,
                "title": current_cards[card_id].get("title", ""),
                "description": current_cards[card_id].get("description", ""),
            }
            for card_id in added_ids
        ]

        cards_removed = [
            {
                "id": card_id,
                "title": previous_cards[card_id].get("title", ""),
                "description": previous_cards[card_id].get("description", ""),
            }
            for card_id in removed_ids
        ]

        cards_changed = []
        for card_id in common_ids:
            curr = current_cards[card_id]
            prev = previous_cards[card_id]

            title_changed = curr.get("title", "") != prev.get("title", "")
            desc_changed = curr.get("description", "") != prev.get("description", "")

            if title_changed or desc_changed:
                cards_changed.append(
                    {
                        "id": card_id,
                        "old_title": prev.get("title", ""),
                        "new_title": curr.get("title", ""),
                        "old_description": prev.get("description", ""),
                        "new_description": curr.get("description", ""),
                    }
                )

        return {
            "is_first_run": False,
            "cards_added": cards_added,
            "cards_removed": cards_removed,
            "cards_changed": cards_changed,
        }
