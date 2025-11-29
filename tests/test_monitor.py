"""Tests for the monitor module."""

from pathlib import Path


from taskcards_monitor.monitor import BoardMonitor, BoardState


class TestBoardState:
    """Tests for BoardState class."""

    def test_extract_cards_basic(self):
        """Test extracting cards from board data."""
        data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "Do this"},
                {"id": "card2", "title": "Task 2", "description": ""},
                {"id": "card3", "title": "Task 3", "description": "Do that"},
            ]
        }

        state = BoardState(data)

        assert len(state.cards) == 3
        assert state.cards["card1"]["title"] == "Task 1"
        assert state.cards["card1"]["description"] == "Do this"
        assert state.cards["card2"]["title"] == "Task 2"
        assert state.cards["card2"]["description"] == ""

    def test_extract_cards_empty(self):
        """Test extracting cards when none exist."""
        data = {"cards": []}

        state = BoardState(data)

        assert state.cards == {}

    def test_extract_cards_missing_id(self):
        """Test extracting cards when some missing IDs."""
        data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": ""},
                {"title": "Task 2", "description": ""},  # Missing ID
                {"id": "card3", "title": "Task 3", "description": ""},
            ]
        }

        state = BoardState(data)

        # Should skip card without ID
        assert len(state.cards) == 2
        assert "card1" in state.cards
        assert "card3" in state.cards

    def test_to_dict(self):
        """Test converting state to dictionary."""
        data = {"cards": [{"id": "card1", "title": "Task 1", "description": "Test"}]}

        state = BoardState(data)
        state_dict = state.to_dict()

        assert "timestamp" in state_dict
        assert "cards" in state_dict
        assert state_dict["cards"]["card1"]["title"] == "Task 1"

    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "timestamp": "2023-01-01T00:00:00",
            "cards": {
                "card1": {"title": "Task 1", "description": "Test"},
            },
        }

        state = BoardState.from_dict(data)

        assert state.timestamp == "2023-01-01T00:00:00"
        assert state.cards["card1"]["title"] == "Task 1"


class TestBoardMonitor:
    """Tests for BoardMonitor class."""

    def test_init_creates_state_directory(self, tmp_path):
        """Test that init creates state directory."""
        state_dir = tmp_path / "test_state"
        monitor = BoardMonitor("board123", state_dir=state_dir)

        assert state_dir.exists()
        assert monitor.state_file == state_dir / "board123.json"

    def test_init_uses_default_directory(self):
        """Test that init uses default directory when none specified."""
        monitor = BoardMonitor("board123")

        expected_dir = Path.home() / ".cache" / "taskcards-monitor"
        assert monitor.state_dir == expected_dir
        assert monitor.state_file == expected_dir / "board123.json"

    def test_get_previous_state_no_file(self, tmp_path):
        """Test getting previous state when file doesn't exist."""
        monitor = BoardMonitor("board123", state_dir=tmp_path)

        state = monitor.get_previous_state()

        assert state is None

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading state."""
        data = {"cards": [{"id": "card1", "title": "Task 1", "description": "Test"}]}

        monitor = BoardMonitor("board123", state_dir=tmp_path)
        state = BoardState(data)

        # Save state
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
                {"id": "card1", "title": "Task 1", "description": "Test"},
            ]
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
                {"id": "card1", "title": "Task 1", "description": "Test"},
            ]
        }

        previous = BoardState(data)
        current = BoardState(data)
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
                {"id": "card1", "title": "Task 1", "description": "Test 1"},
            ]
        }

        curr_data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "Test 1"},
                {"id": "card2", "title": "Task 2", "description": "Test 2"},
            ]
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_added"]) == 1
        assert changes["cards_added"][0]["id"] == "card2"
        assert changes["cards_added"][0]["title"] == "Task 2"
        assert changes["cards_added"][0]["description"] == "Test 2"

    def test_detect_cards_removed(self):
        """Test detecting when cards are removed."""
        prev_data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "Test 1"},
                {"id": "card2", "title": "Task 2", "description": "Test 2"},
            ]
        }

        curr_data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "Test 1"},
            ]
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_removed"]) == 1
        assert changes["cards_removed"][0]["id"] == "card2"
        assert changes["cards_removed"][0]["title"] == "Task 2"

    def test_detect_cards_changed_title(self):
        """Test detecting when card titles change."""
        prev_data = {
            "cards": [
                {"id": "card1", "title": "Old Title", "description": "Test"},
            ]
        }

        curr_data = {
            "cards": [
                {"id": "card1", "title": "New Title", "description": "Test"},
            ]
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_changed"]) == 1
        assert changes["cards_changed"][0]["id"] == "card1"
        assert changes["cards_changed"][0]["old_title"] == "Old Title"
        assert changes["cards_changed"][0]["new_title"] == "New Title"

    def test_detect_cards_changed_description(self):
        """Test detecting when card descriptions change."""
        prev_data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "Old description"},
            ]
        }

        curr_data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "New description"},
            ]
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        assert len(changes["cards_changed"]) == 1
        assert changes["cards_changed"][0]["old_description"] == "Old description"
        assert changes["cards_changed"][0]["new_description"] == "New description"

    def test_detect_multiple_changes(self):
        """Test detecting multiple types of changes at once."""
        prev_data = {
            "cards": [
                {"id": "card1", "title": "Task 1", "description": "Test 1"},
                {"id": "card2", "title": "Task 2", "description": "Test 2"},
            ]
        }

        curr_data = {
            "cards": [
                {"id": "card1", "title": "Task 1 Updated", "description": "Test 1"},  # Changed
                {"id": "card3", "title": "Task 3", "description": "Test 3"},  # Added
                # card2 removed
            ]
        }

        previous = BoardState(prev_data)
        current = BoardState(curr_data)
        monitor = BoardMonitor("board123")
        changes = monitor.detect_changes(current, previous)

        # Check all types of changes detected
        assert len(changes["cards_added"]) == 1  # card3
        assert len(changes["cards_removed"]) == 1  # card2
        assert len(changes["cards_changed"]) == 1  # card1
