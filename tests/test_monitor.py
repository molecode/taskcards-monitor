"""Tests for the monitor module."""

import pytest

from taskcards_monitor.database import get_database, init_database
from taskcards_monitor.models import Change, db
from taskcards_monitor.monitor import BoardMonitor, BoardState


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database for tests."""
    db_file = tmp_path / "test.db"
    init_database(db_file)
    return db_file


def test_get_database_returns_shared_instance(db_path):
    """get_database returns the module-level database instance."""
    assert get_database() is db


class TestBoardState:
    """Tests for BoardState class."""

    def test_extract_cards_basic(self):
        """Test extracting cards from basic board data."""
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "description": "Description 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                    "description": "Description 2",
                    "kanbanPosition": {"listId": "col2", "position": 1},
                },
            ]
        }

        state = BoardState(data)

        assert len(state.cards) == 2
        assert state.cards["card1"]["title"] == "Task 1"
        assert state.cards["card2"]["title"] == "Task 2"

    def test_extract_cards_empty(self):
        """Test extracting cards when no cards present."""
        data = {}
        state = BoardState(data)
        assert state.cards == {}

    def test_extract_cards_missing_id(self):
        """Test extracting cards when some cards missing ID."""
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                },
                {
                    "title": "Invalid Card",  # Missing ID
                    "kanbanPosition": {"listId": "col2", "position": 1},
                },
            ]
        }

        state = BoardState(data)

        # Should only extract cards with IDs
        assert len(state.cards) == 1
        assert "card1" in state.cards


class TestBoardMonitor:
    """Tests for BoardMonitor class."""

    def test_init(self, db_path):
        """Test that BoardMonitor initializes correctly."""
        monitor = BoardMonitor("board123")
        assert monitor.board_id == "board123"

    def test_get_previous_state_no_board(self, db_path):
        """Test getting previous state when board doesn't exist."""
        monitor = BoardMonitor("board123")
        state = monitor.get_previous_state()

        assert state is None

    def test_save_and_load_state(self, db_path):
        """Test saving and loading board state."""
        monitor = BoardMonitor("board123")

        data = {
            "id": "board123",
            "name": "Test Board",
            "description": "Test description",
            "lists": [{"id": "list1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "description": "Description",
                    "link": "",
                    "kanbanPosition": {"listId": "list1"},
                    "attachments": [],
                }
            ],
        }

        # Save state
        state = BoardState(data)
        monitor.save_state(state)

        # Load state
        loaded_state = monitor.get_previous_state()

        assert loaded_state is not None
        assert loaded_state.board_name == "Test Board"
        assert len(loaded_state.cards) == 1
        assert loaded_state.cards["card1"]["title"] == "Task 1"

    def test_detect_changes_first_run(self, db_path):
        """Test detecting changes on first run."""
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        current = BoardState(data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, None)

        assert changes.is_first_run is True
        assert changes.cards_count == 1

    def test_detect_changes_no_changes(self, db_path):
        """Test detecting changes when nothing changed."""
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        current = BoardState(data)
        previous = BoardState(data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert changes.is_first_run is False
        assert len(changes.cards_added) == 0
        assert len(changes.cards_removed) == 0
        assert len(changes.cards_modified) == 0

    def test_detect_cards_added(self, db_path):
        """Test detecting when cards are added."""
        prev_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        curr_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                },
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes.cards_added) == 1
        assert changes.cards_added[0].id == "card2"
        assert changes.cards_added[0].title == "Task 2"

    def test_detect_cards_removed(self, db_path):
        """Test detecting when cards are removed."""
        prev_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                },
            ],
        }

        curr_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes.cards_removed) == 1
        assert changes.cards_removed[0].id == "card2"
        assert changes.cards_removed[0].title == "Task 2"

    def test_detect_cards_changed(self, db_path):
        """Test detecting when cards have their title changed."""
        prev_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        curr_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Updated Task 1",
                }
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes.cards_modified) == 1
        assert changes.cards_modified[0].id == "card1"
        assert changes.cards_modified[0].old_title == "Task 1"
        assert changes.cards_modified[0].new_title == "Updated Task 1"

    def test_detect_multiple_changes(self, db_path):
        """Test detecting multiple types of changes at once."""
        prev_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                },
            ],
        }

        curr_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Updated Task 1",  # Changed
                },
                {
                    "id": "card3",
                    "title": "Task 3",  # Added
                },
                # card2 removed
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        # Check all types of changes detected
        assert len(changes.cards_added) == 1  # card3
        assert len(changes.cards_removed) == 1  # card2
        assert len(changes.cards_modified) == 1  # card1

    def test_detect_attachments_added(self, db_path):
        """Test detecting when attachments are added to a card."""
        prev_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "attachments": [],
                }
            ],
        }

        curr_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "attachments": [
                        {
                            "id": "att1",
                            "filename": "document.pdf",
                            "length": "12345",
                        }
                    ],
                }
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes.cards_modified) == 1
        assert len(changes.cards_modified[0].attachments_added) == 1
        assert changes.cards_modified[0].attachments_added[0].filename == "document.pdf"
        assert len(changes.cards_modified[0].attachments_removed) == 0

    def test_detect_attachments_removed(self, db_path):
        """Test detecting when attachments are removed from a card."""
        prev_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "attachments": [
                        {
                            "id": "att1",
                            "filename": "document.pdf",
                            "length": "12345",
                        }
                    ],
                }
            ],
        }

        curr_data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "attachments": [],
                }
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes.cards_modified) == 1
        assert len(changes.cards_modified[0].attachments_removed) == 1
        assert changes.cards_modified[0].attachments_removed[0].filename == "document.pdf"
        assert len(changes.cards_modified[0].attachments_added) == 0


class TestBoardStateHelpers:
    """Tests for BoardState helper methods."""

    @pytest.fixture
    def state(self):
        """A board state with a card in a column."""
        return BoardState(
            {
                "name": "Test Board",
                "description": "Board description",
                "lists": [{"id": "list1", "name": "To Do", "position": 0}],
                "cards": [
                    {
                        "id": "card1",
                        "title": "Task 1",
                        "kanbanPosition": {"listId": "list1"},
                    },
                    {"id": "card2", "title": "Task 2"},
                    {"id": "card3", "title": "Task 3", "kanbanPosition": {"position": 0}},
                    {
                        "id": "card4",
                        "title": "Task 4",
                        "kanbanPosition": {"listId": "unknown-list"},
                    },
                ],
            }
        )

    def test_board_description(self, state):
        assert state.board_description == "Board description"

    def test_get_card_not_found(self, state):
        assert state.get_card("missing") is None

    def test_get_list_not_found(self, state):
        assert state.get_list("missing") is None

    def test_get_card_column_name(self, state):
        assert state.get_card_column_name("card1") == "To Do"

    def test_get_card_column_name_missing_card(self, state):
        assert state.get_card_column_name("missing") is None

    def test_get_card_column_name_no_kanban_position(self, state):
        assert state.get_card_column_name("card2") is None

    def test_get_card_column_name_no_list_id(self, state):
        assert state.get_card_column_name("card3") is None

    def test_get_card_column_name_unknown_list(self, state):
        assert state.get_card_column_name("card4") is None


class TestBoardMonitorPersistence:
    """Tests for BoardMonitor database persistence across multiple runs."""

    @staticmethod
    def make_board_data(cards, lists=None):
        """Build board data with the given cards and lists."""
        return {
            "id": "board123",
            "name": "Test Board",
            "description": "Test description",
            "lists": lists
            if lists is not None
            else [{"id": "list1", "name": "To Do", "position": 0, "color": "blue"}],
            "cards": cards,
        }

    @staticmethod
    def make_card(card_id, title, list_id="list1", attachments=None, description=""):
        """Build a card dict."""
        return {
            "id": card_id,
            "title": title,
            "description": description,
            "link": "",
            "kanbanPosition": {"listId": list_id},
            "attachments": attachments or [],
        }

    def test_save_state_card_modified_logs_change(self, db_path):
        """Modifying a card creates a new version and logs the change."""
        monitor = BoardMonitor("board123")

        monitor.save_state(BoardState(self.make_board_data([self.make_card("card1", "Task 1")])))
        monitor.save_state(
            BoardState(self.make_board_data([self.make_card("card1", "Updated Task 1")]))
        )

        state = monitor.get_previous_state()
        assert state.cards["card1"]["title"] == "Updated Task 1"

        changes = list(Change.select().where(Change.change_type == "card_modified"))
        assert len(changes) == 1
        assert changes[0].card_id == "card1"

    def test_save_state_card_unchanged_no_new_version(self, db_path):
        """Saving an identical state does not log changes."""
        monitor = BoardMonitor("board123")
        data = self.make_board_data([self.make_card("card1", "Task 1")])

        monitor.save_state(BoardState(data))
        monitor.save_state(BoardState(data))

        assert Change.select().count() == 0

    def test_save_state_card_added_logs_change(self, db_path):
        """Adding a card logs a card_added change."""
        monitor = BoardMonitor("board123")

        monitor.save_state(BoardState(self.make_board_data([self.make_card("card1", "Task 1")])))
        monitor.save_state(
            BoardState(
                self.make_board_data(
                    [self.make_card("card1", "Task 1"), self.make_card("card2", "Task 2")]
                )
            )
        )

        changes = list(Change.select().where(Change.change_type == "card_added"))
        assert len(changes) == 1
        assert changes[0].card_id == "card2"

    def test_save_state_card_removed_logs_change(self, db_path):
        """Removing a card logs a card_removed change."""
        monitor = BoardMonitor("board123")

        monitor.save_state(
            BoardState(
                self.make_board_data(
                    [self.make_card("card1", "Task 1"), self.make_card("card2", "Task 2")]
                )
            )
        )
        monitor.save_state(BoardState(self.make_board_data([self.make_card("card1", "Task 1")])))

        state = monitor.get_previous_state()
        assert "card2" not in state.cards

        changes = list(Change.select().where(Change.change_type == "card_removed"))
        assert len(changes) == 1
        assert changes[0].card_id == "card2"

    def test_save_state_list_changes(self, db_path):
        """Lists are versioned when renamed or removed."""
        monitor = BoardMonitor("board123")

        lists_v1 = [
            {"id": "list1", "name": "To Do", "position": 0, "color": "blue"},
            {"id": "list2", "name": "Done", "position": 1, "color": "green"},
        ]
        monitor.save_state(
            BoardState(self.make_board_data([self.make_card("card1", "Task 1")], lists=lists_v1))
        )

        # Rename list1, remove list2
        lists_v2 = [{"id": "list1", "name": "Backlog", "position": 0, "color": "blue"}]
        monitor.save_state(
            BoardState(self.make_board_data([self.make_card("card1", "Task 1")], lists=lists_v2))
        )

        state = monitor.get_previous_state()
        assert len(state.lists) == 1
        assert state.lists[0]["name"] == "Backlog"

    def test_save_state_attachments_added_and_removed(self, db_path):
        """Attachments are tracked across saves and restored on load."""
        monitor = BoardMonitor("board123")

        attachment = {
            "id": "att1",
            "filename": "doc.pdf",
            "downloadLink": "https://example.com/doc.pdf",
            "mimetype": "application/pdf",
            "length": 123,
        }

        monitor.save_state(
            BoardState(
                self.make_board_data([self.make_card("card1", "Task 1", attachments=[attachment])])
            )
        )

        state = monitor.get_previous_state()
        assert len(state.cards["card1"]["attachments"]) == 1
        assert state.cards["card1"]["attachments"][0]["filename"] == "doc.pdf"

        # Remove the attachment
        monitor.save_state(BoardState(self.make_board_data([self.make_card("card1", "Task 1")])))

        state = monitor.get_previous_state()
        assert state.cards["card1"]["attachments"] == []

    def test_save_state_skips_lists_without_id(self, db_path):
        """Lists without an id are ignored when saving."""
        monitor = BoardMonitor("board123")

        lists = [
            {"id": "list1", "name": "To Do", "position": 0},
            {"name": "Broken list without id", "position": 1},
        ]
        monitor.save_state(BoardState(self.make_board_data([], lists=lists)))

        state = monitor.get_previous_state()
        assert len(state.lists) == 1
        assert state.lists[0]["id"] == "list1"

    def test_save_state_updates_board_metadata(self, db_path):
        """Board name and description are updated on subsequent saves."""
        monitor = BoardMonitor("board123")

        monitor.save_state(BoardState(self.make_board_data([])))

        renamed = self.make_board_data([])
        renamed["name"] = "Renamed Board"
        monitor.save_state(BoardState(renamed))

        state = monitor.get_previous_state()
        assert state.board_name == "Renamed Board"
