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
        self.columns = self._extract_columns(data)
        self.cards = self._extract_cards(data)

    def _extract_columns(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract column information from board data.

        Args:
            data: Raw board data

        Returns:
            Dictionary mapping column ID to column info (name, position, etc.)
        """
        columns = {}

        # TaskCards uses 'lists' for columns
        if "lists" in data:
            for col in data["lists"]:
                col_id = col.get("id")
                if col_id:
                    columns[col_id] = {
                        "name": col.get("name", ""),
                        "position": col.get("position", 0),
                        "color": col.get("color"),
                    }

        return columns

    def _extract_cards(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract card information from board data.

        Args:
            data: Raw board data

        Returns:
            Dictionary mapping card ID to card info (title, column, position, etc.)
        """
        cards = {}

        if "cards" in data:
            for card in data["cards"]:
                card_id = card.get("id")
                if card_id:
                    # Handle TaskCards kanbanPosition structure
                    kanban_pos = card.get("kanbanPosition", {})
                    column_id = kanban_pos.get("listId") if kanban_pos else None
                    position = kanban_pos.get("position") if kanban_pos else None

                    cards[card_id] = {
                        "title": card.get("title", ""),
                        "column_id": column_id,
                        "position": position,
                        "description": card.get("description", ""),
                    }

        return cards

    def to_dict(self) -> dict[str, Any]:
        """Convert board state to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "columns": self.columns,
            "cards": self.cards,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardState":
        """Create BoardState from serialized dictionary."""
        state = cls.__new__(cls)
        state.timestamp = data["timestamp"]
        state.columns = data["columns"]
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

        Args:
            current: Current board state
            previous: Previous board state (None if first run)

        Returns:
            Dictionary containing detected changes
        """
        if previous is None:
            return {
                "is_first_run": True,
                "columns_count": len(current.columns),
                "cards_count": len(current.cards),
            }

        changes = {
            "is_first_run": False,
            "columns_added": [],
            "columns_removed": [],
            "columns_renamed": [],
            "cards_added": [],
            "cards_removed": [],
            "cards_moved": [],
        }

        # Detect column changes
        prev_col_ids = set(previous.columns.keys())
        curr_col_ids = set(current.columns.keys())

        # Added columns
        for col_id in curr_col_ids - prev_col_ids:
            changes["columns_added"].append(
                {
                    "id": col_id,
                    "name": current.columns[col_id]["name"],
                }
            )

        # Removed columns
        for col_id in prev_col_ids - curr_col_ids:
            changes["columns_removed"].append(
                {
                    "id": col_id,
                    "name": previous.columns[col_id]["name"],
                }
            )

        # Renamed columns
        for col_id in prev_col_ids & curr_col_ids:
            prev_name = previous.columns[col_id]["name"]
            curr_name = current.columns[col_id]["name"]
            if prev_name != curr_name:
                changes["columns_renamed"].append(
                    {
                        "id": col_id,
                        "old_name": prev_name,
                        "new_name": curr_name,
                    }
                )

        # Detect card changes
        prev_card_ids = set(previous.cards.keys())
        curr_card_ids = set(current.cards.keys())

        # Added cards
        for card_id in curr_card_ids - prev_card_ids:
            card = current.cards[card_id]
            column_name = current.columns.get(card["column_id"], {}).get("name", "Unknown")
            changes["cards_added"].append(
                {
                    "id": card_id,
                    "title": card["title"],
                    "column": column_name,
                }
            )

        # Removed cards
        for card_id in prev_card_ids - curr_card_ids:
            card = previous.cards[card_id]
            column_name = previous.columns.get(card["column_id"], {}).get("name", "Unknown")
            changes["cards_removed"].append(
                {
                    "id": card_id,
                    "title": card["title"],
                    "column": column_name,
                }
            )

        # Moved cards (existing cards that changed columns)
        for card_id in prev_card_ids & curr_card_ids:
            prev_card = previous.cards[card_id]
            curr_card = current.cards[card_id]

            prev_col_id = prev_card["column_id"]
            curr_col_id = curr_card["column_id"]

            if prev_col_id != curr_col_id:
                prev_col_name = previous.columns.get(prev_col_id, {}).get("name", "Unknown")
                curr_col_name = current.columns.get(curr_col_id, {}).get("name", "Unknown")

                changes["cards_moved"].append(
                    {
                        "id": card_id,
                        "title": curr_card["title"],
                        "from_column": prev_col_name,
                        "to_column": curr_col_name,
                    }
                )

        return changes
