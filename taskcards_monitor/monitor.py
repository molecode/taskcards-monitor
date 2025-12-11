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

    @property
    def cards(self) -> dict[str, dict[str, str]]:
        """
        Get cards in simplified format for display compatibility.

        Returns dict of {card_id: {"title": str, "description": str}}
        This maintains backward compatibility with existing display code.
        """
        cards_dict = {}
        cards_list = self.data.get("cards", [])

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
        return self.data.get("lists", [])

    @property
    def board_name(self) -> str:
        """Get the board name."""
        return self.data.get("name", "")

    @property
    def board_description(self) -> str:
        """Get the board description."""
        return self.data.get("description", "")

    def get_card(self, card_id: str) -> dict[str, Any] | None:
        """
        Get full card data by ID.

        Returns complete card object with all fields including kanbanPosition.
        """
        for card in self.data.get("cards", []):
            if card.get("id") == card_id:
                return card
        return None

    def get_list(self, list_id: str) -> dict[str, Any] | None:
        """Get list data by ID."""
        for lst in self.data.get("lists", []):
            if lst.get("id") == list_id:
                return lst
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert board state to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "board": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardState":
        """Create BoardState from serialized dictionary."""
        state = object.__new__(cls)
        state.timestamp = data["timestamp"]
        state.data = data["board"]
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

        # Create sets once for efficient set operations
        current_ids = set(current_cards)
        previous_ids = set(previous_cards)
        added_ids = current_ids - previous_ids
        removed_ids = previous_ids - current_ids
        common_ids = current_ids & previous_ids

        # Build added cards list (avoid repeated lookups)
        cards_added = [
            {
                "id": card_id,
                "title": (card := current_cards[card_id]).get("title", ""),
                "description": card.get("description", ""),
            }
            for card_id in added_ids
        ]

        # Build removed cards list (avoid repeated lookups)
        cards_removed = [
            {
                "id": card_id,
                "title": (card := previous_cards[card_id]).get("title", ""),
                "description": card.get("description", ""),
            }
            for card_id in removed_ids
        ]

        # Build changed cards list (extract values once per card)
        def _get_changed_card(card_id: str) -> dict[str, Any] | None:
            curr = current_cards[card_id]
            prev = previous_cards[card_id]

            curr_title, curr_desc = curr.get("title", ""), curr.get("description", "")
            prev_title, prev_desc = prev.get("title", ""), prev.get("description", "")

            if curr_title != prev_title or curr_desc != prev_desc:
                return {
                    "id": card_id,
                    "old_title": prev_title,
                    "new_title": curr_title,
                    "old_description": prev_desc,
                    "new_description": curr_desc,
                }
            return None

        cards_changed = [card for card_id in common_ids if (card := _get_changed_card(card_id))]

        return {
            "is_first_run": False,
            "cards_added": cards_added,
            "cards_removed": cards_removed,
            "cards_changed": cards_changed,
        }
