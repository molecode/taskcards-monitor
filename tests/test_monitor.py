"""Tests for the monitor module."""

from pathlib import Path


from taskcards_monitor.monitor import BoardMonitor, BoardState


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

    def test_to_dict(self):
        """Test converting board state to dictionary."""
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        state = BoardState(data)
        result = state.to_dict()

        assert "timestamp" in result
        assert "cards" in result
        assert result["cards"] == state.cards

    def test_from_dict(self):
        """Test creating board state from dictionary."""
        data = {
            "timestamp": "2025-01-01T12:00:00",
            "cards": {
                "card1": {
                    "title": "Task 1",
                }
            },
        }

        state = BoardState.from_dict(data)

        assert state.timestamp == "2025-01-01T12:00:00"
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
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        # Save state
        state = BoardState(data)
        monitor.save_state(state)

        # Load state
        loaded_state = monitor.get_previous_state()

        assert loaded_state is not None
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

        assert changes["is_first_run"] is True
        assert changes["cards_count"] == 1

    def test_detect_changes_no_changes(self):
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

        assert changes["is_first_run"] is False
        assert len(changes["cards_added"]) == 0
        assert len(changes["cards_removed"]) == 0
        assert len(changes["cards_changed"]) == 0

    def test_detect_cards_added(self):
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

        assert len(changes["cards_added"]) == 1
        assert changes["cards_added"][0]["id"] == "card2"
        assert changes["cards_added"][0]["title"] == "Task 2"

    def test_detect_cards_removed(self):
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

        assert len(changes["cards_removed"]) == 1
        assert changes["cards_removed"][0]["id"] == "card2"
        assert changes["cards_removed"][0]["title"] == "Task 2"

    def test_detect_cards_changed(self):
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

        assert len(changes["cards_changed"]) == 1
        assert changes["cards_changed"][0]["id"] == "card1"
        assert changes["cards_changed"][0]["old_title"] == "Task 1"
        assert changes["cards_changed"][0]["new_title"] == "Updated Task 1"

    def test_detect_multiple_changes(self):
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
        assert len(changes["cards_added"]) == 1  # card3
        assert len(changes["cards_removed"]) == 1  # card2
        assert len(changes["cards_changed"]) == 1  # card1
