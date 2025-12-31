"""Board monitoring and change detection logic."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .changes import AttachmentData, CardAdded, CardModified, CardRemoved, ChangeSet
from .models import Attachment, Board, Card, Change, List


@dataclass
class BoardState:
    """Represents the state of a TaskCards board at a point in time."""

    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def cards(self) -> dict[str, dict[str, Any]]:
        """
        Get cards in simplified format for display compatibility.

        Returns dict of {card_id: {"title": str, "description": str, "link": str, "attachments": list}}
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
                    "link": card.get("link", ""),
                    "attachments": card.get("attachments", []),
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

    def get_card_column_name(self, card_id: str) -> str | None:
        """Get the column (list) name for a card.

        Args:
            card_id: The card ID

        Returns:
            Column name or None if not found
        """
        card = self.get_card(card_id)
        if not card:
            return None

        kanban_position = card.get("kanbanPosition")
        if not kanban_position:
            return None

        list_id = kanban_position.get("listId")
        if not list_id:
            return None

        list_data = self.get_list(list_id)
        if not list_data:
            return None

        return list_data.get("name")


class BoardMonitor:
    """Monitors a TaskCards board for changes using SQLite database."""

    def __init__(self, board_id: str):
        """
        Initialize the board monitor.

        Args:
            board_id: The board ID to monitor
        """
        self.board_id = board_id

    def get_previous_state(self) -> BoardState | None:
        """
        Load the previously saved state from database.

        Returns:
            BoardState if exists, None otherwise
        """
        # Get board
        board = Board.get_or_none(Board.board_id == self.board_id)
        if not board:
            return None

        # Get current cards (valid_to IS NULL)
        current_cards = (
            Card.select()
            .where((Card.board == board) & (Card.valid_to.is_null()))
            .order_by(Card.card_id)
        )

        # Get current lists
        current_lists = (
            List.select()
            .where((List.board == board) & (List.valid_to.is_null()))
            .order_by(List.position)
        )

        # Get current attachments
        current_attachments = Attachment.select().where(
            (Attachment.board == board) & (Attachment.removed_at.is_null())
        )

        # Build attachments map: card_id -> list of attachments
        attachments_map = {}
        for att in current_attachments:
            if att.card_id not in attachments_map:
                attachments_map[att.card_id] = []
            attachments_map[att.card_id].append(
                {
                    "id": att.attachment_id,
                    "filename": att.filename,
                    "downloadLink": att.url,
                    "mimetype": att.mime_type,
                    "length": att.length,
                }
            )

        # Reconstruct board data structure
        cards_list = []
        for card in current_cards:
            card_data = {
                "id": card.card_id,
                "title": card.title,
                "description": card.description,
                "link": card.link,
                "attachments": attachments_map.get(card.card_id, []),
            }

            # Add kanbanPosition if we have list info
            if card.list_id:
                card_data["kanbanPosition"] = {"listId": card.list_id}

            cards_list.append(card_data)

        lists_list = [
            {
                "id": lst.list_id,
                "name": lst.name,
                "position": lst.position,
                "color": lst.color,
            }
            for lst in current_lists
        ]

        data = {
            "id": board.board_id,
            "name": board.name,
            "description": board.description,
            "cards": cards_list,
            "lists": lists_list,
        }

        return BoardState(data=data, timestamp=board.last_checked.isoformat())

    def save_state(self, state: BoardState) -> None:
        """
        Save the current board state to database.

        This method:
        1. Updates or creates the board record
        2. Compares with previous state to create historical records
        3. Updates temporal tables (cards, lists, attachments)
        4. Records changes in the changes table

        Args:
            state: BoardState to save
        """
        now = datetime.now()
        board_id = state.data.get("id")

        # Get or create board
        board, created = Board.get_or_create(
            board_id=board_id,
            defaults={
                "name": state.board_name,
                "description": state.board_description,
                "first_checked": now,
                "last_checked": now,
            },
        )

        if not created:
            board.name = state.board_name
            board.description = state.board_description
            board.last_checked = now
            board.save()

        # Get previous state for comparison
        previous = self.get_previous_state() if not created else None

        # Save lists
        self._save_lists(board, state.lists, now)

        # Save cards and detect changes
        changes = self._save_cards(board, state, previous, now)

        # Save attachments
        self._save_attachments(board, state, now)

        # Log changes if not first run
        if previous is not None and changes:
            self._log_changes(board, changes, now)

    def _save_lists(self, board: Board, lists: list[dict[str, Any]], timestamp: datetime) -> None:
        """Save lists to database with temporal tracking."""
        # Get current lists
        current_lists = {
            lst.list_id: lst
            for lst in List.select().where((List.board == board) & (List.valid_to.is_null()))
        }

        new_list_ids = {lst.get("id") for lst in lists if lst.get("id")}

        # Mark removed lists as invalid
        for list_id, lst in current_lists.items():
            if list_id not in new_list_ids:
                lst.valid_to = timestamp
                lst.save()

        # Add or update lists
        for lst_data in lists:
            list_id = lst_data.get("id")
            if not list_id:
                continue

            name = lst_data.get("name", "")
            position = lst_data.get("position")
            color = lst_data.get("color")

            existing = current_lists.get(list_id)

            # Check if anything changed
            if existing:
                if (
                    existing.name == name
                    and existing.position == position
                    and existing.color == color
                ):
                    continue  # No change

                # Mark old as invalid
                existing.valid_to = timestamp
                existing.save()

            # Create new version
            List.create(
                board=board,
                list_id=list_id,
                name=name,
                position=position,
                color=color,
                valid_from=timestamp,
                valid_to=None,
            )

    def _save_cards(
        self,
        board: Board,
        state: BoardState,
        previous: BoardState | None,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Save cards to database and return detected changes."""
        # Get current cards
        current_cards = {
            card.card_id: card
            for card in Card.select().where((Card.board == board) & (Card.valid_to.is_null()))
        }

        new_cards_data = {card.get("id"): card for card in state.data.get("cards", [])}
        new_card_ids = set(new_cards_data.keys())
        current_card_ids = set(current_cards.keys())

        changes = {
            "cards_added": [],
            "cards_removed": [],
            "cards_changed": [],
        }

        # Detect removed cards
        for card_id in current_card_ids - new_card_ids:
            card = current_cards[card_id]
            card.valid_to = timestamp
            card.save()

            if previous:
                changes["cards_removed"].append(
                    {
                        "id": card_id,
                        "title": card.title,
                        "description": card.description,
                        "link": card.link,
                        "column": card.list_name,
                        "attachments": [],
                    }
                )

        # Detect added and modified cards
        for card_id in new_card_ids:
            card_data = new_cards_data[card_id]
            title = card_data.get("title", "")
            description = card_data.get("description", "")
            link = card_data.get("link", "")

            kanban_pos = card_data.get("kanbanPosition", {})
            list_id = kanban_pos.get("listId")
            list_name = state.get_card_column_name(card_id)

            existing = current_cards.get(card_id)

            if card_id in current_card_ids:
                # Check if anything changed
                if (
                    existing.title == title
                    and existing.description == description
                    and existing.link == link
                    and existing.list_id == list_id
                ):
                    continue  # No change

                # Card modified
                if previous:
                    changes["cards_changed"].append(
                        {
                            "id": card_id,
                            "old_title": existing.title,
                            "new_title": title,
                            "old_description": existing.description,
                            "new_description": description,
                            "old_link": existing.link,
                            "new_link": link,
                            "old_column": existing.list_name,
                            "new_column": list_name,
                            "attachments_added": [],
                            "attachments_removed": [],
                        }
                    )

                # Mark old as invalid
                existing.valid_to = timestamp
                existing.save()
            else:
                # Card added
                if previous:
                    changes["cards_added"].append(
                        {
                            "id": card_id,
                            "title": title,
                            "description": description,
                            "link": link,
                            "column": list_name,
                            "attachments": [],
                        }
                    )

            # Create new version
            Card.create(
                board=board,
                card_id=card_id,
                title=title,
                description=description,
                link=link,
                list_id=list_id,
                list_name=list_name,
                valid_from=timestamp,
                valid_to=None,
            )

        return changes

    def _save_attachments(self, board: Board, state: BoardState, timestamp: datetime) -> None:
        """Save attachments to database with temporal tracking."""
        # Get current attachments
        current_attachments = {}
        for att in Attachment.select().where(
            (Attachment.board == board) & (Attachment.removed_at.is_null())
        ):
            key = (att.card_id, att.attachment_id)
            current_attachments[key] = att

        # Build map of new attachments
        new_attachments = {}
        for card in state.data.get("cards", []):
            card_id = card.get("id")
            for att_data in card.get("attachments", []):
                att_id = att_data.get("id")
                if card_id and att_id:
                    key = (card_id, att_id)
                    new_attachments[key] = att_data

        # Mark removed attachments
        for key, att in current_attachments.items():
            if key not in new_attachments:
                att.removed_at = timestamp
                att.save()

        # Add new attachments
        for key, att_data in new_attachments.items():
            if key not in current_attachments:
                card_id, att_id = key
                Attachment.create(
                    board=board,
                    card_id=card_id,
                    attachment_id=att_id,
                    filename=att_data.get("filename"),
                    url=att_data.get("downloadLink"),
                    mime_type=att_data.get("mimetype"),
                    length=att_data.get("length"),
                    added_at=timestamp,
                    removed_at=None,
                )

    def _log_changes(self, board: Board, changes: dict[str, Any], timestamp: datetime) -> None:
        """Log changes in the changes table."""
        # Record added cards
        for card in changes.get("cards_added", []):
            Change.create(
                board=board,
                timestamp=timestamp,
                change_type="card_added",
                card_id=card["id"],
                details=json.dumps(card),
            )

        # Record removed cards
        for card in changes.get("cards_removed", []):
            Change.create(
                board=board,
                timestamp=timestamp,
                change_type="card_removed",
                card_id=card["id"],
                details=json.dumps(card),
            )

        # Record modified cards
        for card in changes.get("cards_changed", []):
            Change.create(
                board=board,
                timestamp=timestamp,
                change_type="card_modified",
                card_id=card["id"],
                details=json.dumps(card),
            )

    def detect_changes(self, current: BoardState, previous: BoardState | None) -> ChangeSet:
        """
        Detect changes between current and previous board states.

        Args:
            current: Current board state
            previous: Previous board state (None if first run)

        Returns:
            ChangeSet containing detected changes
        """
        current_cards = current.cards
        previous_cards = previous.cards if previous else {}

        if previous is None:
            return ChangeSet(
                is_first_run=True,
                cards_count=len(current_cards),
                cards_added=[],
                cards_removed=[],
                cards_modified=[],
            )

        # Create sets once for efficient set operations
        current_ids = set(current_cards)
        previous_ids = set(previous_cards)
        added_ids = current_ids - previous_ids
        removed_ids = previous_ids - current_ids
        common_ids = current_ids & previous_ids

        # Build added cards list (avoid repeated lookups)
        cards_added = [
            CardAdded(
                id=card_id,
                title=(card := current_cards[card_id]).get("title", ""),
                description=card.get("description", ""),
                link=card.get("link", ""),
                column=current.get_card_column_name(card_id),
                attachments=[AttachmentData.from_dict(att) for att in card.get("attachments", [])],
            )
            for card_id in added_ids
        ]

        # Build removed cards list (avoid repeated lookups)
        cards_removed = [
            CardRemoved(
                id=card_id,
                title=(card := previous_cards[card_id]).get("title", ""),
                description=card.get("description", ""),
                link=card.get("link", ""),
                column=previous.get_card_column_name(card_id),
                attachments=[AttachmentData.from_dict(att) for att in card.get("attachments", [])],
            )
            for card_id in removed_ids
        ]

        # Build changed cards list (extract values once per card)
        def _get_changed_card(card_id: str) -> CardModified | None:
            curr = current_cards[card_id]
            prev = previous_cards[card_id]

            curr_title, curr_desc = curr.get("title", ""), curr.get("description", "")
            prev_title, prev_desc = prev.get("title", ""), prev.get("description", "")
            curr_link = curr.get("link", "")
            prev_link = prev.get("link", "")
            curr_attachments = curr.get("attachments", [])
            prev_attachments = prev.get("attachments", [])

            curr_column = current.get_card_column_name(card_id)
            prev_column = previous.get_card_column_name(card_id)

            # Compare attachments by ID
            curr_attachment_ids = {att.get("id") for att in curr_attachments}
            prev_attachment_ids = {att.get("id") for att in prev_attachments}
            attachments_changed = curr_attachment_ids != prev_attachment_ids

            if (
                curr_title != prev_title
                or curr_desc != prev_desc
                or curr_link != prev_link
                or curr_column != prev_column
                or attachments_changed
            ):
                # Find added and removed attachments
                added_attachment_ids = curr_attachment_ids - prev_attachment_ids
                removed_attachment_ids = prev_attachment_ids - curr_attachment_ids

                added_attachments = [
                    AttachmentData.from_dict(att)
                    for att in curr_attachments
                    if att.get("id") in added_attachment_ids
                ]
                removed_attachments = [
                    AttachmentData.from_dict(att)
                    for att in prev_attachments
                    if att.get("id") in removed_attachment_ids
                ]

                return CardModified(
                    id=card_id,
                    old_title=prev_title,
                    new_title=curr_title,
                    old_description=prev_desc,
                    new_description=curr_desc,
                    old_link=prev_link,
                    new_link=curr_link,
                    old_column=prev_column,
                    new_column=curr_column,
                    attachments_added=added_attachments,
                    attachments_removed=removed_attachments,
                )
            return None

        cards_changed = [card for card_id in common_ids if (card := _get_changed_card(card_id))]

        return ChangeSet(
            is_first_run=False,
            cards_added=cards_added,
            cards_removed=cards_removed,
            cards_modified=cards_changed,
        )
