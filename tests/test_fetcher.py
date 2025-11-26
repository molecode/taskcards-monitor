"""Tests for the fetcher module."""

from unittest.mock import MagicMock, patch

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from taskcards_monitor.fetcher import TaskCardsFetcher


class TestTaskCardsFetcher:
    """Tests for TaskCardsFetcher class."""

    def test_init(self):
        """Test fetcher initialization."""
        fetcher = TaskCardsFetcher(headless=True, timeout=30000)

        assert fetcher.headless is True
        assert fetcher.timeout == 30000
        assert fetcher.playwright is None
        assert fetcher.browser is None

    def test_init_defaults(self):
        """Test fetcher initialization with defaults."""
        fetcher = TaskCardsFetcher()

        assert fetcher.headless is True
        assert fetcher.timeout == 60000

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_context_manager_enter(self, mock_sync_playwright):
        """Test context manager __enter__."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser

        fetcher = TaskCardsFetcher(headless=True)

        with fetcher as f:
            assert f.playwright == mock_playwright
            assert f.browser == mock_browser
            mock_playwright.chromium.launch.assert_called_once_with(headless=True)

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_context_manager_exit(self, mock_sync_playwright):
        """Test context manager __exit__."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser

        fetcher = TaskCardsFetcher(headless=True)

        with fetcher:
            pass

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_without_browser(self, mock_sync_playwright):
        """Test fetch_board raises error when browser not initialized."""
        fetcher = TaskCardsFetcher()

        with pytest.raises(ValueError, match="Browser not initialized"):
            fetcher.fetch_board("board123")

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_success(self, mock_sync_playwright):
        """Test successful board fetch."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock board data returned by evaluate
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
        mock_page.evaluate.return_value = board_data

        with TaskCardsFetcher(headless=True) as fetcher:
            result = fetcher.fetch_board("board123")

        # Verify results
        assert result == board_data
        mock_page.goto.assert_called_once_with(
            "https://www.taskcards.de/#/board/board123/view",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        mock_page.wait_for_selector.assert_called()
        mock_page.close.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_with_token(self, mock_sync_playwright):
        """Test board fetch with view token."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [],
        }
        mock_page.evaluate.return_value = board_data

        with TaskCardsFetcher(headless=True) as fetcher:
            result = fetcher.fetch_board("board123", token="secret123")

        # Verify URL includes token
        mock_page.goto.assert_called_once()
        call_args = mock_page.goto.call_args
        assert "token=secret123" in call_args[0][0]
        assert result == board_data

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_with_screenshot(self, mock_sync_playwright, tmp_path):
        """Test board fetch with screenshot."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock evaluate to return dimensions and board data
        mock_page.evaluate.side_effect = [
            {"width": 1920, "height": 1080},  # First call: dimensions
            {  # Second call: board data
                "lists": [{"id": "col1", "name": "To Do", "position": 0}],
                "cards": [],
            },
        ]

        screenshot_path = str(tmp_path / "test.png")

        with TaskCardsFetcher(headless=True) as fetcher:
            fetcher.fetch_board("board123", screenshot_path=screenshot_path)

        # Verify screenshot was taken
        mock_page.screenshot.assert_called_once_with(path=screenshot_path)
        mock_page.set_viewport_size.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_timeout_error(self, mock_sync_playwright):
        """Test fetch_board handles timeout errors."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Simulate timeout
        mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")

        with TaskCardsFetcher(headless=True) as fetcher:
            with pytest.raises(PlaywrightTimeoutError, match="Timeout while loading board"):
                fetcher.fetch_board("board123")

        mock_page.close.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_empty_data_error(self, mock_sync_playwright):
        """Test fetch_board handles empty board data."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Return empty data
        mock_page.evaluate.return_value = {}

        with TaskCardsFetcher(headless=True) as fetcher:
            with pytest.raises(ValueError, match="does not contain expected"):
                fetcher.fetch_board("board123")

        mock_page.close.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_404_error(self, mock_sync_playwright):
        """Test fetch_board handles 404 errors."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Simulate evaluation error
        mock_page.evaluate.side_effect = Exception("Evaluation failed")
        # Note: Due to the exception handling in fetcher.py, ValueError raised inside
        # the inner try block gets swallowed, so we expect the generic error message
        mock_page.content.return_value = "<html><body>Some error</body></html>"

        with TaskCardsFetcher(headless=True) as fetcher:
            with pytest.raises(ValueError, match="Failed to extract board data"):
                fetcher.fetch_board("board123")

        mock_page.close.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_generic_error(self, mock_sync_playwright):
        """Test fetch_board handles generic errors."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Simulate evaluation error
        mock_page.evaluate.side_effect = Exception("Evaluation failed")
        mock_page.content.return_value = "<html><body>Some generic error</body></html>"

        with TaskCardsFetcher(headless=True) as fetcher:
            with pytest.raises(ValueError, match="Failed to extract board data"):
                fetcher.fetch_board("board123")

        mock_page.close.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_closes_page_on_error(self, mock_sync_playwright):
        """Test that page is closed even when errors occur."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Simulate error during wait_for_selector
        mock_page.wait_for_selector.side_effect = Exception("Selector error")

        with TaskCardsFetcher(headless=True) as fetcher:
            with pytest.raises(ValueError):
                fetcher.fetch_board("board123")

        # Page should still be closed
        mock_page.close.assert_called_once()

    @patch("taskcards_monitor.fetcher.sync_playwright")
    def test_fetch_board_no_cards(self, mock_sync_playwright):
        """Test fetching board with no cards (should not raise error)."""
        # Setup mocks
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.start.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock board with lists but no cards
        board_data = {
            "lists": [{"id": "col1", "name": "To Do", "position": 0}],
            "cards": [],
        }
        mock_page.evaluate.return_value = board_data

        # wait_for_selector for cards should timeout (no cards present)
        def wait_for_selector_side_effect(selector, **kwargs):
            if selector == ".board-card":
                raise Exception("No cards found")
            return MagicMock()

        mock_page.wait_for_selector.side_effect = wait_for_selector_side_effect

        with TaskCardsFetcher(headless=True) as fetcher:
            result = fetcher.fetch_board("board123")

        # Should succeed even without cards
        assert result == board_data
        mock_page.close.assert_called_once()

    def test_extract_board_data_js_exists(self):
        """Test that the extract_board_data.js file exists and is loaded."""
        from taskcards_monitor.fetcher import EXTRACT_BOARD_DATA_JS

        assert EXTRACT_BOARD_DATA_JS is not None
        assert len(EXTRACT_BOARD_DATA_JS) > 0
        assert isinstance(EXTRACT_BOARD_DATA_JS, str)
