"""Tests for the monitor module."""

from pathlib import Path


from taskcards_monitor.monitor import BoardMonitor, BoardState


class TestBoardState:
    """Tests for BoardState class."""

    def test_extract_columns_basic(self):
        """Test extracting columns from basic board data."""
        data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0, "color": "#ff0000"},
                {"id": "col2", "name": "In Progress", "position": 1, "color": "#00ff00"},
                {"id": "col3", "name": "Done", "position": 2, "color": "#0000ff"},
            ]
        }

        state = BoardState(data)

        assert len(state.columns) == 3
        assert state.columns["col1"]["name"] == "To Do"
        assert state.columns["col1"]["position"] == 0
        assert state.columns["col1"]["color"] == "#ff0000"
        assert state.columns["col2"]["name"] == "In Progress"
        assert state.columns["col3"]["name"] == "Done"

    def test_extract_columns_empty(self):
        """Test extracting columns when no lists present."""
        data = {}
        state = BoardState(data)
        assert state.columns == {}

    def test_extract_columns_missing_id(self):
        """Test extracting columns when some lists missing ID."""
        data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0},
                {"name": "Invalid Column", "position": 1},  # Missing ID
                {"id": "col2", "name": "Done", "position": 2},
            ]
        }

        state = BoardState(data)

        # Should only extract columns with IDs
        assert len(state.columns) == 2
        assert "col1" in state.columns
        assert "col2" in state.columns

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
        assert state.cards["card1"]["column_id"] == "col1"
        assert state.cards["card1"]["position"] == 0
        assert state.cards["card1"]["description"] == "Description 1"
        assert state.cards["card2"]["column_id"] == "col2"

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

    def test_extract_cards_no_kanban_position(self):
        """Test extracting cards when kanbanPosition is missing or empty."""
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                    # No kanbanPosition
                },
                {
                    "id": "card3",
                    "title": "Task 3",
                    "kanbanPosition": {},  # Empty kanbanPosition
                },
            ]
        }

        state = BoardState(data)

        assert len(state.cards) == 3
        assert state.cards["card1"]["column_id"] == "col1"
        assert state.cards["card2"]["column_id"] is None
        assert state.cards["card2"]["position"] is None
        assert state.cards["card3"]["column_id"] is None

    def test_to_dict(self):
        """Test converting board state to dictionary."""
        data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        state = BoardState(data)
        result = state.to_dict()

        assert "timestamp" in result
        assert "columns" in result
        assert "cards" in result
        assert result["columns"] == state.columns
        assert result["cards"] == state.cards

    def test_from_dict(self):
        """Test creating board state from dictionary."""
        data = {
            "timestamp": "2025-01-01T12:00:00",
            "columns": {"col1": {"name": "To Do", "position": 0, "color": None}},
            "cards": {
                "card1": {
                    "title": "Task 1",
                    "column_id": "col1",
                    "position": 0,
                    "description": "",
                }
            },
        }

        state = BoardState.from_dict(data)

        assert state.timestamp == "2025-01-01T12:00:00"
        assert state.columns == data["columns"]
        assert state.cards == data["cards"]
        assert state.raw_data == {}


class TestBoardMonitor:
    """Tests for BoardMonitor class."""

    def test_init_creates_state_directory(self, tmp_path):
        """Test that BoardMonitor creates state directory on init."""
        state_dir = tmp_path / "test_state"
        monitor = BoardMonitor("board123", state_dir=state_dir)

        assert state_dir.exists()
        assert state_dir.is_dir()
        assert monitor.board_id == "board123"
        assert monitor.state_file == state_dir / "board123.json"

    def test_init_uses_default_directory(self):
        """Test that BoardMonitor uses default directory when not specified."""
        monitor = BoardMonitor("board123")

        expected_dir = Path.home() / ".cache" / "taskcards-monitor"
        assert monitor.state_dir == expected_dir
        assert monitor.state_file == expected_dir / "board123.json"

    def test_get_previous_state_no_file(self, tmp_path):
        """Test getting previous state when no state file exists."""
        monitor = BoardMonitor("board123", state_dir=tmp_path)
        state = monitor.get_previous_state()

        assert state is None

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading board state."""
        monitor = BoardMonitor("board123", state_dir=tmp_path)

        data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        # Save state
        state = BoardState(data)
        monitor.save_state(state)

        # Load state
        loaded_state = monitor.get_previous_state()

        assert loaded_state is not None
        assert loaded_state.columns == state.columns
        assert loaded_state.cards == state.cards

    def test_get_previous_state_corrupted_file(self, tmp_path):
        """Test getting previous state when file is corrupted."""
        monitor = BoardMonitor("board123", state_dir=tmp_path)

        # Create corrupted JSON file
        with open(monitor.state_file, "w") as f:
            f.write("{ invalid json")

        state = monitor.get_previous_state()
        assert state is None

    def test_detect_changes_first_run(self):
        """Test detecting changes on first run."""
        data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        current = BoardState(data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, None)

        assert changes["is_first_run"] is True
        assert changes["columns_count"] == 1
        assert changes["cards_count"] == 1

    def test_detect_changes_no_changes(self):
        """Test detecting changes when nothing changed."""
        data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        current = BoardState(data)
        previous = BoardState(data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert changes["is_first_run"] is False
        assert len(changes["columns_added"]) == 0
        assert len(changes["columns_removed"]) == 0
        assert len(changes["columns_renamed"]) == 0
        assert len(changes["cards_added"]) == 0
        assert len(changes["cards_removed"]) == 0
        assert len(changes["cards_moved"]) == 0

    def test_detect_columns_added(self):
        """Test detecting when columns are added."""
        prev_data = {"lists": [{"id": "col1", "name": "To Do", "position": 0}]}

        curr_data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0},
                {"id": "col2", "name": "In Progress", "position": 1},
            ]
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["columns_added"]) == 1
        assert changes["columns_added"][0]["id"] == "col2"
        assert changes["columns_added"][0]["name"] == "In Progress"

    def test_detect_columns_removed(self):
        """Test detecting when columns are removed."""
        prev_data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0},
                {"id": "col2", "name": "In Progress", "position": 1},
            ]
        }

        curr_data = {"lists": [{"id": "col1", "name": "To Do", "position": 0}]}

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["columns_removed"]) == 1
        assert changes["columns_removed"][0]["id"] == "col2"
        assert changes["columns_removed"][0]["name"] == "In Progress"

    def test_detect_columns_renamed(self):
        """Test detecting when columns are renamed."""
        prev_data = {"lists": [{"id": "col1", "name": "To Do", "position": 0}]}

        curr_data = {"lists": [{"id": "col1", "name": "TODO", "position": 0}]}

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["columns_renamed"]) == 1
        assert changes["columns_renamed"][0]["id"] == "col1"
        assert changes["columns_renamed"][0]["old_name"] == "To Do"
        assert changes["columns_renamed"][0]["new_name"] == "TODO"

    def test_detect_cards_added(self):
        """Test detecting when cards are added."""
        prev_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        curr_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                    "kanbanPosition": {"listId": "col1", "position": 1},
                },
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_added"]) == 1
        assert changes["cards_added"][0]["id"] == "card2"
        assert changes["cards_added"][0]["title"] == "Task 2"
        assert changes["cards_added"][0]["column"] == "To Do"

    def test_detect_cards_removed(self):
        """Test detecting when cards are removed."""
        prev_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                    "kanbanPosition": {"listId": "col1", "position": 1},
                },
            ],
        }

        curr_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_removed"]) == 1
        assert changes["cards_removed"][0]["id"] == "card2"
        assert changes["cards_removed"][0]["title"] == "Task 2"
        assert changes["cards_removed"][0]["column"] == "To Do"

    def test_detect_cards_moved(self):
        """Test detecting when cards are moved between columns."""
        prev_data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0},
                {"id": "col2", "name": "Done", "position": 1},
            ],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }

        curr_data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0},
                {"id": "col2", "name": "Done", "position": 1},
            ],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col2", "position": 0},
                }
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_moved"]) == 1
        assert changes["cards_moved"][0]["id"] == "card1"
        assert changes["cards_moved"][0]["title"] == "Task 1"
        assert changes["cards_moved"][0]["from_column"] == "To Do"
        assert changes["cards_moved"][0]["to_column"] == "Done"

    def test_detect_multiple_changes(self):
        """Test detecting multiple types of changes at once."""
        prev_data = {
            "lists": [
                {"id": "col1", "name": "To Do", "position": 0},
                {"id": "col2", "name": "Done", "position": 1},
            ],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                },
                {
                    "id": "card2",
                    "title": "Task 2",
                    "kanbanPosition": {"listId": "col1", "position": 1},
                },
            ],
        }

        curr_data = {
            "lists": [
                {"id": "col1", "name": "TODO", "position": 0},  # Renamed
                {"id": "col3", "name": "In Progress", "position": 1},  # Added
            ],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col3", "position": 0},  # Moved
                },
                {
                    "id": "card3",
                    "title": "Task 3",
                    "kanbanPosition": {"listId": "col1", "position": 0},  # Added
                },
                # card2 removed
            ],
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        # Check all types of changes detected
        assert len(changes["columns_added"]) == 1  # col3
        assert len(changes["columns_removed"]) == 1  # col2
        assert len(changes["columns_renamed"]) == 1  # col1
        assert len(changes["cards_added"]) == 1  # card3
        assert len(changes["cards_removed"]) == 1  # card2
        assert len(changes["cards_moved"]) == 1  # card1
