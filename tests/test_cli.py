"""Tests for the CLI module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from taskcards_monitor.cli import main
from taskcards_monitor.monitor import BoardState


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    def test_main_help(self, runner):
        """Test main command with --help."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Monitor TaskCards boards for changes" in result.output

    def test_main_version(self, runner):
        """Test main command with --version."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_check_command_first_run(self, mock_monitor_class, mock_fetcher_class, runner):
        """Test check command on first run."""
        # Setup mocks
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor
        mock_monitor.get_previous_state.return_value = None

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher

        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }
        mock_fetcher.fetch_board.return_value = board_data

        # Run command
        result = runner.invoke(main, ["check", "board123"])

        # Verify
        assert result.exit_code == 0
        assert "First Run" in result.output or "Initial state saved" in result.output
        mock_monitor_class.assert_called_once_with("board123")
        mock_fetcher.fetch_board.assert_called_once_with("board123", token=None)
        mock_monitor.save_state.assert_called_once()

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_check_command_with_token(self, mock_monitor_class, mock_fetcher_class, runner):
        """Test check command with token option."""
        # Setup mocks
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor
        mock_monitor.get_previous_state.return_value = None

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher

        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [],
        }
        mock_fetcher.fetch_board.return_value = board_data

        # Run command with token
        result = runner.invoke(main, ["check", "board123", "--token", "secret123"])

        # Verify
        assert result.exit_code == 0
        mock_fetcher.fetch_board.assert_called_once_with("board123", token="secret123")

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_check_command_verbose(self, mock_monitor_class, mock_fetcher_class, runner):
        """Test check command with verbose flag."""
        # Setup mocks
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor
        mock_monitor.get_previous_state.return_value = None
        mock_monitor.state_file = Path("/tmp/board123.json")

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher

        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [],
        }
        mock_fetcher.fetch_board.return_value = board_data

        # Run command with verbose
        result = runner.invoke(main, ["check", "board123", "-v"])

        # Verify verbose output
        assert result.exit_code == 0
        assert "Checking board" in result.output

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_check_command_no_changes(self, mock_monitor_class, mock_fetcher_class, runner):
        """Test check command when no changes detected."""
        # Setup mocks
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Previous state exists
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
        prev_state = BoardState(prev_data)
        mock_monitor.get_previous_state.return_value = prev_state

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher
        mock_fetcher.fetch_board.return_value = prev_data

        # Run command
        result = runner.invoke(main, ["check", "board123"])

        # Verify
        assert result.exit_code == 0
        # Check for the "No changes" message (may be formatted with Rich styling)
        assert "No changes" in result.output or "changes detected" not in result.output.lower()

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_check_command_with_changes(self, mock_monitor_class, mock_fetcher_class, runner):
        """Test check command when changes are detected."""
        # Setup mocks
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Previous state
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
        prev_state = BoardState(prev_data)
        mock_monitor.get_previous_state.return_value = prev_state

        # Current state with new card
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

        # Mock detect_changes to return changes with a new card added
        mock_monitor.detect_changes.return_value = {
            "is_first_run": False,
            "cards_added": [{"id": "card2", "title": "Task 2"}],
            "cards_removed": [],
            "cards_changed": [],
        }

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher
        mock_fetcher.fetch_board.return_value = curr_data

        # Run command
        result = runner.invoke(main, ["check", "board123"])

        # Verify - should show changes (Task 2 was added)
        assert result.exit_code == 0
        # Check that it shows changes
        assert (
            "Changes detected" in result.output
            or "Cards Added" in result.output
            or "Task 2" in result.output
        )

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_check_command_fetch_error(self, mock_monitor_class, mock_fetcher_class, runner):
        """Test check command when fetch fails."""
        # Setup mocks
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor
        mock_monitor.get_previous_state.return_value = None

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher
        mock_fetcher.fetch_board.side_effect = Exception("Network error")

        # Run command
        result = runner.invoke(main, ["check", "board123"])

        # Verify error handling
        assert result.exit_code != 0
        assert "Error" in result.output

    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_show_command(self, mock_monitor_class, runner):
        """Test show command."""
        # Setup mock
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Create board state
        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }
        state = BoardState(data)
        mock_monitor.get_previous_state.return_value = state

        # Run command
        result = runner.invoke(main, ["show", "board123"])

        # Verify
        assert result.exit_code == 0
        assert "Board State" in result.output
        assert "Task 1" in result.output

    @patch("taskcards_monitor.cli.BoardMonitor")
    def test_show_command_no_state(self, mock_monitor_class, runner):
        """Test show command when no saved state exists."""
        # Setup mock
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor
        mock_monitor.get_previous_state.return_value = None

        # Run command
        result = runner.invoke(main, ["show", "board123"])

        # Verify
        assert result.exit_code == 0
        assert "No saved state found" in result.output

    def test_list_command_no_boards(self, runner, tmp_path):
        """Test list command when no boards have been checked."""
        with patch("taskcards_monitor.cli.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            result = runner.invoke(main, ["list"])

        # Verify
        assert result.exit_code == 0
        assert "No boards have been checked yet" in result.output

    def test_list_command_with_boards(self, runner, tmp_path):
        """Test list command with existing boards."""
        # Create state directory
        state_dir = tmp_path / ".cache" / "taskcards-monitor"
        state_dir.mkdir(parents=True)

        # Create state files
        board1_data = {
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

        board2_data = {
            "timestamp": "2025-01-02T12:00:00",
            "columns": {
                "col1": {"name": "To Do", "position": 0, "color": None},
                "col2": {"name": "Done", "position": 1, "color": None},
            },
            "cards": {},
        }

        with open(state_dir / "board123.json", "w") as f:
            json.dump(board1_data, f)

        with open(state_dir / "board456.json", "w") as f:
            json.dump(board2_data, f)

        with patch("taskcards_monitor.cli.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            result = runner.invoke(main, ["list"])

        # Verify
        assert result.exit_code == 0
        assert "Monitored Boards" in result.output
        assert "board123" in result.output
        assert "board456" in result.output

    def test_list_command_with_malformed_file(self, runner, tmp_path):
        """Test list command skips malformed state files."""
        # Create state directory
        state_dir = tmp_path / ".cache" / "taskcards-monitor"
        state_dir.mkdir(parents=True)

        # Create valid state file
        valid_data = {
            "timestamp": "2025-01-01T12:00:00",
            "columns": {},
            "cards": {},
        }
        with open(state_dir / "board123.json", "w") as f:
            json.dump(valid_data, f)

        # Create malformed state file
        with open(state_dir / "board456.json", "w") as f:
            f.write("{ invalid json")

        with patch("taskcards_monitor.cli.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            result = runner.invoke(main, ["list"])

        # Verify - should only show valid board
        assert result.exit_code == 0
        assert "board123" in result.output
        assert "board456" not in result.output

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    def test_inspect_command(self, mock_fetcher_class, runner):
        """Test inspect command."""
        # Setup mock
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher

        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                    "kanbanPosition": {"listId": "col1", "position": 0},
                }
            ],
        }
        mock_fetcher.fetch_board.return_value = board_data

        # Run command
        result = runner.invoke(main, ["inspect", "board123"])

        # Verify
        assert result.exit_code == 0
        assert "Inspect Mode" in result.output
        assert "Board loaded successfully" in result.output
        mock_fetcher_class.assert_called_once_with(headless=False)
        mock_fetcher.fetch_board.assert_called_once_with(
            "board123", token=None, screenshot_path=None
        )

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    def test_inspect_command_with_token_and_screenshot(self, mock_fetcher_class, runner, tmp_path):
        """Test inspect command with token and screenshot."""
        # Setup mock
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher

        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [],
        }
        mock_fetcher.fetch_board.return_value = board_data

        screenshot_path = str(tmp_path / "test.png")

        # Run command
        result = runner.invoke(
            main, ["inspect", "board123", "--token", "secret123", "--screenshot", screenshot_path]
        )

        # Verify
        assert result.exit_code == 0
        mock_fetcher.fetch_board.assert_called_once_with(
            "board123", token="secret123", screenshot_path=screenshot_path
        )

    @patch("taskcards_monitor.cli.TaskCardsFetcher")
    def test_inspect_command_error(self, mock_fetcher_class, runner):
        """Test inspect command when fetch fails."""
        # Setup mock
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value.__enter__.return_value = mock_fetcher
        mock_fetcher.fetch_board.side_effect = Exception("Network error")

        # Run command
        result = runner.invoke(main, ["inspect", "board123"])

        # Verify error handling
        assert result.exit_code != 0
        assert "Error" in result.output


class TestDisplayFunctions:
    """Tests for display helper functions."""

    def test_create_table(self):
        """Test create_table helper function."""
        from taskcards_monitor.cli import create_table

        table = create_table(
            title="Test Table",
            header_style="bold blue",
            columns=[
                {"name": "Column 1", "style": "green"},
                {"name": "Column 2", "style": "red"},
            ],
            rows=[("Row 1 Col 1", "Row 1 Col 2"), ("Row 2 Col 1", "Row 2 Col 2")],
        )

        # Basic checks - table should be created
        assert table is not None
        assert table.title == "Test Table"

    def test_display_changes_first_run(self, capsys):
        """Test display_changes for first run."""
        from taskcards_monitor.cli import display_changes

        changes = {"is_first_run": True, "columns_count": 3, "cards_count": 5}

        display_changes(changes)

        captured = capsys.readouterr()
        assert "First Run" in captured.out or "Initial state saved" in captured.out

    def test_display_changes_no_changes(self, capsys):
        """Test display_changes when no changes detected."""
        from taskcards_monitor.cli import display_changes

        changes = {
            "is_first_run": False,
            "cards_added": [],
            "cards_removed": [],
            "cards_changed": [],
        }

        display_changes(changes)

        captured = capsys.readouterr()
        assert "No changes detected" in captured.out

    def test_display_state(self, capsys):
        """Test display_state function."""
        from taskcards_monitor.cli import display_state

        data = {
            "cards": [
                {
                    "id": "card1",
                    "title": "Task 1",
                }
            ],
        }

        state = BoardState(data)
        display_state(state)

        captured = capsys.readouterr()
        assert "Board State" in captured.out
        assert "Task 1" in captured.out
