"""Tests for the display module."""

import json
from datetime import datetime
from types import SimpleNamespace

from taskcards_monitor.changes import (
    AttachmentData,
    CardAdded,
    CardModified,
    CardRemoved,
    ChangeSet,
)
import pytest

from taskcards_monitor.display import (
    _format_attachments,
    _format_link,
    console,
    display_boards_list,
    display_changes,
    display_history,
    display_inspect_header,
    display_inspect_results,
    display_state,
)
from taskcards_monitor.monitor import BoardState


@pytest.fixture(autouse=True)
def wide_console():
    """Widen the Rich console so table cells are not wrapped mid-word."""
    original = console._width
    console.width = 300
    yield
    console._width = original


def make_attachment(att_id: str, filename: str) -> AttachmentData:
    """Create an AttachmentData instance for tests."""
    return AttachmentData(
        id=att_id,
        filename=filename,
        download_link=f"https://example.com/{filename}",
        mime_type="application/pdf",
        length=123,
    )


class TestFormatters:
    """Tests for formatting helpers."""

    def test_format_link_empty(self):
        assert _format_link("") == "[dim]<none>[/dim]"

    def test_format_link_value(self):
        assert _format_link("https://example.com") == "https://example.com"

    def test_format_attachments_empty(self):
        assert _format_attachments([]) == "[dim]<none>[/dim]"

    def test_format_attachments_few(self):
        attachments = [make_attachment("a1", "doc.pdf")]
        result = _format_attachments(attachments)
        assert "1 file(s)" in result
        assert "doc.pdf" in result
        assert "..." not in result

    def test_format_attachments_truncated(self):
        attachments = [make_attachment(f"a{i}", f"file{i}.pdf") for i in range(5)]
        result = _format_attachments(attachments)
        assert "5 file(s)" in result
        assert "..." in result


class TestDisplayChanges:
    """Tests for display_changes."""

    def test_cards_added(self, capsys):
        changes = ChangeSet(
            is_first_run=False,
            cards_added=[
                CardAdded(
                    id="card1",
                    title="New Task",
                    description="Description",
                    link="https://example.com",
                    column="To Do",
                    attachments=[make_attachment("a1", "doc.pdf")],
                )
            ],
        )

        display_changes(changes)

        out = capsys.readouterr().out
        assert "Changes detected" in out
        assert "Cards Added" in out
        assert "New Task" in out

    def test_cards_removed(self, capsys):
        changes = ChangeSet(
            is_first_run=False,
            cards_removed=[
                CardRemoved(
                    id="card1",
                    title="Old Task",
                    description="",
                    link="",
                    column=None,
                    attachments=[],
                )
            ],
        )

        display_changes(changes)

        out = capsys.readouterr().out
        assert "Cards Removed" in out
        assert "Old Task" in out

    def test_cards_modified_all_fields(self, capsys):
        changes = ChangeSet(
            is_first_run=False,
            cards_modified=[
                CardModified(
                    id="card1",
                    old_title="Old Title",
                    new_title="New Title",
                    old_description="Old desc",
                    new_description="New desc",
                    old_link="https://old.example.com",
                    new_link="https://new.example.com",
                    old_column="To Do",
                    new_column="Done",
                    attachments_added=[make_attachment("a1", "new.pdf")],
                    attachments_removed=[make_attachment("a2", "old.pdf")],
                )
            ],
        )

        display_changes(changes)

        out = capsys.readouterr().out
        assert "Cards Changed" in out
        assert "New Title" in out

    def test_cards_modified_title_only(self, capsys):
        changes = ChangeSet(
            is_first_run=False,
            cards_modified=[
                CardModified(
                    id="card1",
                    old_title="Old Title",
                    new_title="New Title",
                    old_description="",
                    new_description="",
                    old_link="",
                    new_link="",
                    old_column=None,
                    new_column=None,
                )
            ],
        )

        display_changes(changes)

        out = capsys.readouterr().out
        assert "Cards Changed" in out
        assert "New Title" in out
        assert "unchanged" in out

    def test_cards_modified_attachments_only_added(self, capsys):
        changes = ChangeSet(
            is_first_run=False,
            cards_modified=[
                CardModified(
                    id="card1",
                    old_title="Task",
                    new_title="Task",
                    old_description="",
                    new_description="",
                    old_link="",
                    new_link="",
                    old_column=None,
                    new_column=None,
                    attachments_added=[make_attachment(f"a{i}", f"file{i}.pdf") for i in range(3)],
                    attachments_removed=[],
                )
            ],
        )

        display_changes(changes)

        out = capsys.readouterr().out
        assert "Cards Changed" in out
        assert "+3" in out

    def test_cards_modified_attachments_only_removed(self, capsys):
        changes = ChangeSet(
            is_first_run=False,
            cards_modified=[
                CardModified(
                    id="card1",
                    old_title="Task",
                    new_title="Task",
                    old_description="",
                    new_description="",
                    old_link="",
                    new_link="",
                    old_column=None,
                    new_column=None,
                    attachments_added=[],
                    attachments_removed=[make_attachment("a1", "gone.pdf")],
                )
            ],
        )

        display_changes(changes)

        out = capsys.readouterr().out
        assert "Cards Changed" in out
        assert "-1" in out


class TestDisplayState:
    """Tests for display_state and board details."""

    def test_display_state_full_board(self, capsys):
        data = {
            "name": "Test Board",
            "lists": [
                {"id": "list1", "name": "To Do", "position": 0},
                {"id": "list2", "name": "Done", "position": 1},
            ],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "description": "Description",
                    "link": "https://example.com",
                    "kanbanPosition": {"listId": "list1"},
                    "attachments": [],
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                    # No kanbanPosition -> no column
                },
            ],
        }

        display_state(BoardState(data))

        out = capsys.readouterr().out
        assert "Test Board" in out
        assert "Columns" in out
        assert "To Do" in out
        assert "Task 1" in out
        assert "Total: 2 cards" in out

    def test_display_state_no_cards(self, capsys):
        display_state(BoardState({"name": "Empty Board", "lists": [], "cards": []}))

        out = capsys.readouterr().out
        assert "No cards found" in out


class TestDisplayBoardsList:
    """Tests for display_boards_list."""

    def test_display_boards(self, capsys):
        boards_info = [
            {
                "board_id": "board123",
                "board_name": "My Board",
                "timestamp": "2026-01-01T12:00:00",
                "cards": 3,
            }
        ]

        display_boards_list(boards_info)

        out = capsys.readouterr().out
        assert "Monitored Boards (1 total)" in out
        assert "board123" in out
        assert "My Board" in out


class TestDisplayInspect:
    """Tests for inspect display helpers."""

    def test_header_with_name(self, capsys):
        display_inspect_header("board123", "My Board")

        out = capsys.readouterr().out
        assert "Inspect Mode" in out
        assert "board123" in out
        assert "My Board" in out

    def test_header_without_name(self, capsys):
        display_inspect_header("board123")

        out = capsys.readouterr().out
        assert "board123" in out
        assert "Board Name" not in out

    def test_inspect_results(self, capsys):
        data = {
            "lists": [{"id": "list1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "list1"},
                }
            ],
        }

        display_inspect_results(BoardState(data))

        out = capsys.readouterr().out
        assert "Board loaded successfully" in out
        assert "Total Columns: 1" in out
        assert "Total Cards: 1" in out


class TestDisplayHistory:
    """Tests for display_history."""

    @staticmethod
    def make_change(change_type: str, details: dict) -> SimpleNamespace:
        """Create a fake Change model instance."""
        return SimpleNamespace(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            change_type=change_type,
            card_id="card1",
            details=json.dumps(details),
        )

    def test_no_changes(self, capsys):
        display_history("My Board", [])

        out = capsys.readouterr().out
        assert "No changes found" in out

    def test_card_added(self, capsys):
        changes = [self.make_change("card_added", {"title": "New Task", "column": "To Do"})]

        display_history("My Board", changes)

        out = capsys.readouterr().out
        assert "Change History" in out
        assert "Added" in out
        assert "New Task" in out
        assert "To Do" in out

    def test_card_removed(self, capsys):
        changes = [self.make_change("card_removed", {"title": "Old Task", "column": "Done"})]

        display_history("My Board", changes)

        out = capsys.readouterr().out
        assert "Removed" in out
        assert "Old Task" in out

    def test_card_modified(self, capsys):
        changes = [
            self.make_change(
                "card_modified",
                {
                    "old_title": "Old",
                    "new_title": "New",
                    "old_column": "To Do",
                    "new_column": "Done",
                    "old_description": "a",
                    "new_description": "b",
                    "old_link": "x",
                    "new_link": "y",
                },
            )
        ]

        display_history("My Board", changes)

        out = capsys.readouterr().out
        assert "Modified" in out
        assert "description changed" in out
        assert "link changed" in out

    def test_card_modified_no_diff_details(self, capsys):
        changes = [self.make_change("card_modified", {"old_title": "Same", "new_title": "Same"})]

        display_history("My Board", changes)

        out = capsys.readouterr().out
        assert "modified" in out

    def test_unknown_change_type(self, capsys):
        changes = [self.make_change("card_moved", {"info": "somewhere"})]

        display_history("My Board", changes)

        out = capsys.readouterr().out
        assert "Moved" in out
