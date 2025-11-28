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


def _build_card_title_mapping(state: BoardState) -> dict[str, dict[str, Any]]:
    """Build a mapping of card titles to card info for a board state."""
    card_titles = {}
    for card_id, card_data in state.cards.items():
        col_name = state.columns.get(card_data["column_id"], {}).get("name", "Unknown")
        title = card_data["title"]
        card_titles[title] = {
            "id": card_id,
            "column_name": col_name,
            "data": card_data,
        }
    return card_titles


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

        Uses NAME-BASED matching instead of ID-based matching because TaskCards
        reassigns column IDs when columns are inserted in the middle.

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
            "columns_moved": [],
            "cards_added": [],
            "cards_removed": [],
            "cards_moved": [],
        }

        # Build name-based mappings (since TaskCards reassigns IDs)
        prev_names = {data["name"]: (col_id, data) for col_id, data in previous.columns.items()}
        curr_names = {data["name"]: (col_id, data) for col_id, data in current.columns.items()}

        prev_name_set = set(prev_names.keys())
        curr_name_set = set(curr_names.keys())

        # Added columns (new names that didn't exist before)
        # Build position mapping at the same time for rename detection
        added_by_position = {}
        for col_name in curr_name_set - prev_name_set:
            col_id, col_data = curr_names[col_name]
            pos = col_data["position"]
            changes["columns_added"].append(
                {
                    "id": col_id,
                    "name": col_name,
                    "position": pos,
                }
            )
            added_by_position[pos] = (col_name, col_id)

        # Removed columns (names that no longer exist)
        # Build position mapping at the same time for rename detection
        removed_by_position = {}
        for col_name in prev_name_set - curr_name_set:
            col_id, col_data = prev_names[col_name]
            pos = col_data["position"]
            changes["columns_removed"].append(
                {
                    "id": col_id,
                    "name": col_name,
                    "position": pos,
                }
            )
            removed_by_position[pos] = (col_name, col_id)

        # Existing columns (same name) - check for position changes
        for col_name in prev_name_set & curr_name_set:
            prev_col_id, prev_col = prev_names[col_name]
            curr_col_id, curr_col = curr_names[col_name]

            prev_pos = prev_col["position"]
            curr_pos = curr_col["position"]

            # Moved columns (position changed)
            if prev_pos != curr_pos:
                changes["columns_moved"].append(
                    {
                        "id": curr_col_id,
                        "name": col_name,
                        "old_position": prev_pos,
                        "new_position": curr_pos,
                    }
                )

        # Find positions where both a remove and add occurred
        rename_positions = set(removed_by_position.keys()) & set(added_by_position.keys())

        # Track names that were actually renamed (not just removed/added)
        renamed_old_names = set()
        renamed_new_names = set()

        for pos in rename_positions:
            old_name, old_id = removed_by_position[pos]
            new_name, new_id = added_by_position[pos]

            # Only treat as rename if IDs match (same column, different name)
            # If IDs differ, it's a true remove+add (one column deleted, another added)
            if old_id == new_id:
                changes["columns_renamed"].append(
                    {
                        "id": new_id,
                        "old_name": old_name,
                        "new_name": new_name,
                        "position": pos,
                    }
                )
                renamed_old_names.add(old_name)
                renamed_new_names.add(new_name)

        # Remove renamed columns from added and removed lists (if any renames occurred)
        if renamed_new_names:
            changes["columns_added"] = [
                c for c in changes["columns_added"] if c["name"] not in renamed_new_names
            ]
        if renamed_old_names:
            changes["columns_removed"] = [
                c for c in changes["columns_removed"] if c["name"] not in renamed_old_names
            ]

        # Detect card changes (use TITLE-based matching since IDs also change)
        prev_card_titles = _build_card_title_mapping(previous)
        curr_card_titles = _build_card_title_mapping(current)

        prev_title_set = set(prev_card_titles.keys())
        curr_title_set = set(curr_card_titles.keys())

        # Added cards (new titles)
        for title in curr_title_set - prev_title_set:
            card_info = curr_card_titles[title]
            changes["cards_added"].append(
                {
                    "id": card_info["id"],
                    "title": title,
                    "column": card_info["column_name"],
                }
            )

        # Removed cards (titles that no longer exist)
        for title in prev_title_set - curr_title_set:
            card_info = prev_card_titles[title]
            changes["cards_removed"].append(
                {
                    "id": card_info["id"],
                    "title": title,
                    "column": card_info["column_name"],
                }
            )

        # Moved cards (existing cards that changed columns)
        for title in prev_title_set & curr_title_set:
            prev_info = prev_card_titles[title]
            curr_info = curr_card_titles[title]

            prev_col_name = prev_info["column_name"]
            curr_col_name = curr_info["column_name"]

            # Only report as "moved" if the column NAME changed
            if prev_col_name != curr_col_name:
                changes["cards_moved"].append(
                    {
                        "id": curr_info["id"],
                        "title": title,
                        "from_column": prev_col_name,
                        "to_column": curr_col_name,
                    }
                )

        return changes
