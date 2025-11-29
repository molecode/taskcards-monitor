"""Board monitoring and change detection logic."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ColumnChange:
    """Represents a column that was added or removed."""

    id: str
    name: str
    position: int


@dataclass
class ColumnRename:
    """Represents a column that was renamed."""

    id: str
    old_name: str
    new_name: str
    position: int


@dataclass
class ColumnMove:
    """Represents a column that changed position."""

    id: str
    name: str
    old_position: int
    new_position: int


@dataclass
class CardChange:
    """Represents a card that was added or removed."""

    id: str
    title: str
    column: str


@dataclass
class CardRename:
    """Represents a card that was renamed."""

    id: str
    old_title: str
    new_title: str
    column: str


@dataclass
class CardMove:
    """Represents a card that moved between columns."""

    id: str
    title: str
    from_column: str
    to_column: str


@dataclass
class BoardChanges:
    """Container for all detected board changes."""

    is_first_run: bool = False
    columns_count: int = 0
    cards_count: int = 0
    columns_added: list[ColumnChange] = field(default_factory=list)
    columns_removed: list[ColumnChange] = field(default_factory=list)
    columns_renamed: list[ColumnRename] = field(default_factory=list)
    columns_moved: list[ColumnMove] = field(default_factory=list)
    cards_added: list[CardChange] = field(default_factory=list)
    cards_removed: list[CardChange] = field(default_factory=list)
    cards_renamed: list[CardRename] = field(default_factory=list)
    cards_moved: list[CardMove] = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access for backward compatibility."""
        dict_repr = self.to_dict()
        return dict_repr[key]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility with display code."""
        if self.is_first_run:
            return {
                "is_first_run": True,
                "columns_count": self.columns_count,
                "cards_count": self.cards_count,
            }

        return {
            "is_first_run": False,
            "columns_added": [
                {"id": c.id, "name": c.name, "position": c.position} for c in self.columns_added
            ],
            "columns_removed": [
                {"id": c.id, "name": c.name, "position": c.position} for c in self.columns_removed
            ],
            "columns_renamed": [
                {
                    "id": c.id,
                    "old_name": c.old_name,
                    "new_name": c.new_name,
                    "position": c.position,
                }
                for c in self.columns_renamed
            ],
            "columns_moved": [
                {
                    "id": c.id,
                    "name": c.name,
                    "old_position": c.old_position,
                    "new_position": c.new_position,
                }
                for c in self.columns_moved
            ],
            "cards_added": [
                {"id": c.id, "title": c.title, "column": c.column} for c in self.cards_added
            ],
            "cards_removed": [
                {"id": c.id, "title": c.title, "column": c.column} for c in self.cards_removed
            ],
            "cards_renamed": [
                {
                    "id": c.id,
                    "old_title": c.old_title,
                    "new_title": c.new_title,
                    "column": c.column,
                }
                for c in self.cards_renamed
            ],
            "cards_moved": [
                {
                    "id": c.id,
                    "title": c.title,
                    "from_column": c.from_column,
                    "to_column": c.to_column,
                }
                for c in self.cards_moved
            ],
        }


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

    @staticmethod
    def _build_card_title_mapping(state: BoardState) -> dict[str, dict[str, Any]]:
        """Build a mapping of card titles to card info for a board state."""
        card_titles = {}
        for card_id, card_data in state.cards.items():
            col_id = card_data["column_id"]
            col_name = state.columns.get(col_id, {}).get("name", "Unknown")
            title = card_data["title"]
            card_titles[title] = {
                "id": card_id,
                "column_id": col_id,
                "column_name": col_name,
                "data": card_data,
            }
        return card_titles

    @staticmethod
    def _build_column_name_mappings(
        state: BoardState,
    ) -> tuple[dict[str, tuple[str, dict]], set[str]]:
        """Build name-based column mappings and name set."""
        names = {data["name"]: (col_id, data) for col_id, data in state.columns.items()}
        return names, set(names.keys())

    @staticmethod
    def _filter_renamed_items(
        items: list[dict], renamed_names: set[str], name_key: str
    ) -> list[dict]:
        """Filter out renamed items from added/removed lists."""
        if not renamed_names:
            return items
        return [item for item in items if item[name_key] not in renamed_names]

    def _detect_column_changes(
        self,
        current: BoardState,
        previous: BoardState,
        prev_names: dict[str, tuple[str, dict]],
        curr_names: dict[str, tuple[str, dict]],
        prev_name_set: set[str],
        curr_name_set: set[str],
    ) -> dict[str, list]:
        """
        Detect column changes (added, removed, renamed, moved).

        Args:
            current: Current board state
            previous: Previous board state
            prev_names: Previous column name mappings
            curr_names: Current column name mappings
            prev_name_set: Set of previous column names
            curr_name_set: Set of current column names

        Returns:
            Dictionary with column change lists
        """
        changes = {
            "columns_added": [],
            "columns_removed": [],
            "columns_renamed": [],
            "columns_moved": [],
        }

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
        changes["columns_added"] = self._filter_renamed_items(
            changes["columns_added"], renamed_new_names, "name"
        )
        changes["columns_removed"] = self._filter_renamed_items(
            changes["columns_removed"], renamed_old_names, "name"
        )

        return changes

    def _detect_card_changes(
        self,
        current: BoardState,
        previous: BoardState,
        column_renames: list[dict],
        prev_name_set: set,
        curr_name_set: set,
    ) -> dict[str, list]:
        """
        Detect card changes (added, removed, renamed, moved).

        Args:
            current: Current board state
            previous: Previous board state
            column_renames: List of renamed columns
            prev_name_set: Set of previous column names
            curr_name_set: Set of current column names

        Returns:
            Dictionary with card change lists
        """
        changes = {
            "cards_added": [],
            "cards_removed": [],
            "cards_renamed": [],
            "cards_moved": [],
        }

        # Build title-based mappings
        prev_card_titles = self._build_card_title_mapping(previous)
        curr_card_titles = self._build_card_title_mapping(current)

        prev_title_set = set(prev_card_titles.keys())
        curr_title_set = set(curr_card_titles.keys())

        # Build ID-based mappings for added/removed cards to detect renames
        removed_cards_by_id = {}
        for title in prev_title_set - curr_title_set:
            card_info = prev_card_titles[title]
            card_id = card_info["id"]
            changes["cards_removed"].append(
                {
                    "id": card_id,
                    "title": title,
                    "column": card_info["column_name"],
                }
            )
            removed_cards_by_id[card_id] = (title, card_info)

        # Added cards (new titles) - build ID mapping for rename detection
        added_cards_by_id = {}
        for title in curr_title_set - prev_title_set:
            card_info = curr_card_titles[title]
            card_id = card_info["id"]
            changes["cards_added"].append(
                {
                    "id": card_id,
                    "title": title,
                    "column": card_info["column_name"],
                }
            )
            added_cards_by_id[card_id] = (title, card_info)

        # Build a mapping from previous column names to current column names
        # This helps us detect if a column was renamed
        prev_col_name_to_curr_name = {}
        for col_name in prev_name_set & curr_name_set:
            prev_col_name_to_curr_name[col_name] = col_name

        # For renamed columns, map old name to new name
        for rename_info in column_renames:
            old_name = rename_info["old_name"]
            new_name = rename_info["new_name"]
            prev_col_name_to_curr_name[old_name] = new_name

        # Moved cards (existing cards that changed columns)
        for title in prev_title_set & curr_title_set:
            prev_info = prev_card_titles[title]
            curr_info = curr_card_titles[title]

            prev_col_name = prev_info["column_name"]
            curr_col_name = curr_info["column_name"]

            # Map the previous column name to what it is now (accounting for renames)
            expected_col_name = prev_col_name_to_curr_name.get(prev_col_name, prev_col_name)

            # Only report as "moved" if the current column is different from expected
            # This accounts for:
            # - Column renames: card stays in renamed column (not a move)
            # - Column ID changes: card stays in same-named column (not a move)
            # - Actual moves: card is now in a different column name
            if curr_col_name != expected_col_name:
                changes["cards_moved"].append(
                    {
                        "id": curr_info["id"],
                        "title": title,
                        "from_column": prev_col_name,
                        "to_column": curr_col_name,
                    }
                )

        # Detect renames: if a card ID was removed and the same ID was added with different title
        # This means the card was renamed (same position/ID, different title)
        renamed_card_ids = set(removed_cards_by_id.keys()) & set(added_cards_by_id.keys())

        # Track renamed cards to remove them from added/removed lists
        renamed_old_titles = set()
        renamed_new_titles = set()

        for card_id in renamed_card_ids:
            old_title, old_info = removed_cards_by_id[card_id]
            new_title, new_info = added_cards_by_id[card_id]

            # Same ID and same column = rename (not a remove+add of different cards)
            if old_info["column_id"] == new_info["column_id"]:
                changes["cards_renamed"].append(
                    {
                        "id": card_id,
                        "old_title": old_title,
                        "new_title": new_title,
                        "column": new_info["column_name"],
                    }
                )
                renamed_old_titles.add(old_title)
                renamed_new_titles.add(new_title)

        # Remove renamed cards from added and removed lists
        changes["cards_added"] = self._filter_renamed_items(
            changes["cards_added"], renamed_new_titles, "title"
        )
        changes["cards_removed"] = self._filter_renamed_items(
            changes["cards_removed"], renamed_old_titles, "title"
        )

        return changes

    def detect_changes(self, current: BoardState, previous: BoardState | None) -> BoardChanges:
        """
        Detect changes between current and previous board states.

        Uses NAME-BASED matching instead of ID-based matching because TaskCards
        reassigns column IDs when columns are inserted in the middle.

        Args:
            current: Current board state
            previous: Previous board state (None if first run)

        Returns:
            BoardChanges object containing all detected changes
        """
        if previous is None:
            return BoardChanges(
                is_first_run=True,
                columns_count=len(current.columns),
                cards_count=len(current.cards),
            )

        # Build column name mappings (used by both column and card detection)
        prev_names, prev_name_set = self._build_column_name_mappings(previous)
        curr_names, curr_name_set = self._build_column_name_mappings(current)

        # Detect column changes
        column_changes = self._detect_column_changes(
            current, previous, prev_names, curr_names, prev_name_set, curr_name_set
        )

        # Detect card changes
        card_changes = self._detect_card_changes(
            current, previous, column_changes["columns_renamed"], prev_name_set, curr_name_set
        )

        # Build and return BoardChanges dataclass
        return BoardChanges(
            is_first_run=False,
            columns_added=[
                ColumnChange(id=c["id"], name=c["name"], position=c["position"])
                for c in column_changes["columns_added"]
            ],
            columns_removed=[
                ColumnChange(id=c["id"], name=c["name"], position=c["position"])
                for c in column_changes["columns_removed"]
            ],
            columns_renamed=[
                ColumnRename(
                    id=c["id"],
                    old_name=c["old_name"],
                    new_name=c["new_name"],
                    position=c["position"],
                )
                for c in column_changes["columns_renamed"]
            ],
            columns_moved=[
                ColumnMove(
                    id=c["id"],
                    name=c["name"],
                    old_position=c["old_position"],
                    new_position=c["new_position"],
                )
                for c in column_changes["columns_moved"]
            ],
            cards_added=[
                CardChange(id=c["id"], title=c["title"], column=c["column"])
                for c in card_changes["cards_added"]
            ],
            cards_removed=[
                CardChange(id=c["id"], title=c["title"], column=c["column"])
                for c in card_changes["cards_removed"]
            ],
            cards_renamed=[
                CardRename(
                    id=c["id"],
                    old_title=c["old_title"],
                    new_title=c["new_title"],
                    column=c["column"],
                )
                for c in card_changes["cards_renamed"]
            ],
            cards_moved=[
                CardMove(
                    id=c["id"],
                    title=c["title"],
                    from_column=c["from_column"],
                    to_column=c["to_column"],
                )
                for c in card_changes["cards_moved"]
            ],
        )
