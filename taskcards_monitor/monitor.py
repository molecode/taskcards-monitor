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
    cards: dict[str, dict[str, str]] = field(default_factory=dict, init=False)
    raw_data: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        """Extract card data from raw board data after initialization."""
        self.raw_data = self.data
        self.cards = {}

        if "cards" in self.data:
            for card in self.data["cards"]:
                card_id = card.get("id")
                if card_id:
                    self.cards[card_id] = {
                        "title": card.get("title", ""),
                    }

    def to_dict(self) -> dict[str, Any]:
        """Convert board state to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "cards": self.cards,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardState":
        """Create BoardState from serialized dictionary."""
        state = object.__new__(cls)
        state.timestamp = data["timestamp"]
        state.cards = data["cards"]
        state.raw_data = {}
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

        # Detect card changes
        prev_card_ids = set(previous.cards.keys())
        curr_card_ids = set(current.cards.keys())

        # Added cards
        for card_id in curr_card_ids - prev_card_ids:
            card = current.cards[card_id]
            changes["cards_added"].append(
                {
                    "id": card_id,
                    "title": card["title"],
                }
            )

        # Removed cards
        for card_id in prev_card_ids - curr_card_ids:
            card = previous.cards[card_id]
            changes["cards_removed"].append(
                {
                    "id": card_id,
                    "title": card["title"],
                }
            )

        # Changed cards (existing cards that changed title)
        for card_id in prev_card_ids & curr_card_ids:
            prev_card = previous.cards[card_id]
            curr_card = current.cards[card_id]

            if prev_card["title"] != curr_card["title"]:
                changes["cards_changed"].append(
                    {
                        "id": card_id,
                        "old_title": prev_card["title"],
                        "new_title": curr_card["title"],
                    }
                )

        return changes
