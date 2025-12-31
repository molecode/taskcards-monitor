"""Tests for the monitor module."""

import pytest

from taskcards_monitor.database import init_database
from taskcards_monitor.monitor import BoardMonitor, BoardState


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database for tests."""
    db_file = tmp_path / "test.db"
    init_database(db_file)
    return db_file


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
