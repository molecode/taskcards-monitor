"""Tests for the fetcher module."""

from unittest.mock import MagicMock

import httpx
import pytest

from taskcards_monitor.fetcher import TaskCardsFetcher


class TestTaskCardsFetcher:
    """Tests for TaskCardsFetcher class."""

    def test_init_defaults(self):
        """Fetcher initializes with default values."""
        fetcher = TaskCardsFetcher()

        assert fetcher.timeout == 60
        assert fetcher.client is None
        assert fetcher.x_token is None

    def test_context_manager_creates_client(self):
        """Context manager should create and close httpx client."""
        fetcher = TaskCardsFetcher(timeout=5)

        with fetcher as f:
            assert f.client is not None
            assert isinstance(f.client, httpx.Client)

        # Client is closed after exiting context
        assert fetcher.client is not None
        assert fetcher.client.is_closed

    def test_create_visitor_success(self):
        """Visitor creation stores returned id."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()

        response = MagicMock()
        response.json.return_value = {"data": {"createVisitor": {"id": "visitor123"}}}
        response.raise_for_status.return_value = None
        fetcher.client.post.return_value = response

        visitor_id = fetcher._create_visitor()

        assert visitor_id == "visitor123"
        fetcher.client.post.assert_called_once()

    def test_create_visitor_missing_id_raises(self):
        """Visitor creation without id raises error."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()

        response = MagicMock()
        response.json.return_value = {"data": {"createVisitor": {}}}
        response.raise_for_status.return_value = None
        fetcher.client.post.return_value = response

        with pytest.raises(ValueError, match="Failed to get visitor ID"):
            fetcher._create_visitor()

    def test_grant_access_success(self):
        """Granting access posts to correct URL with token."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()
        fetcher.x_token = "visitor123"

        response = MagicMock()
        response.raise_for_status.return_value = None
        fetcher.client.post.return_value = response

        fetcher._grant_access("board123", "token123")

        fetcher.client.post.assert_called_once()
        call_args = fetcher.client.post.call_args
        assert call_args.kwargs["headers"] == {"x-token": "visitor123"}

    def test_grant_access_http_error(self):
        """Grant access surfaces http errors."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()
        fetcher.x_token = "visitor123"

        response = MagicMock()
        http_error = httpx.HTTPStatusError(
            "fail",
            request=httpx.Request("POST", "https://example.com"),
            response=httpx.Response(404, request=httpx.Request("POST", "https://example.com")),
        )
        response.raise_for_status.side_effect = http_error
        fetcher.client.post.return_value = response

        with pytest.raises(ValueError, match="not found"):
            fetcher._grant_access("board123", "badtoken")

    def test_fetch_board_requires_client(self):
        """fetch_board without context raises error."""
        fetcher = TaskCardsFetcher()

        with pytest.raises(ValueError, match="Client not initialized"):
            fetcher.fetch_board("board123")

    def test_fetch_board_success(self):
        """Successful fetch returns normalized data."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()

        fetcher._create_visitor = MagicMock(return_value="visitor123")  # type: ignore
        fetcher._grant_access = MagicMock()  # type: ignore

        response = MagicMock()
        response.json.return_value = {
            "data": {
                "board": {
                    "id": "board123",
                    "lists": [{"id": "list1"}],
                    "cards": [{"id": "card1"}],
                }
            }
        }
        response.raise_for_status.return_value = None
        fetcher.client.post.return_value = response

        result = fetcher.fetch_board("board123", token="secret")

        fetcher._create_visitor.assert_called_once()  # type: ignore
        fetcher._grant_access.assert_called_once_with("board123", "secret")  # type: ignore
        # After simplification, fetch_board returns board data directly (not wrapped)
        assert result["id"] == "board123"
        assert result["lists"] == [{"id": "list1"}]
        assert result["cards"] == [{"id": "card1"}]

    def test_fetch_board_graphql_error(self):
        """GraphQL errors are surfaced as ValueError."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()
        fetcher._create_visitor = MagicMock(return_value="visitor123")  # type: ignore

        response = MagicMock()
        response.json.return_value = {
            "errors": [
                {
                    "message": "Not found",
                    "extensions": {"code": "BOARD_ERROR"},
                }
            ]
        }
        response.raise_for_status.return_value = None
        fetcher.client.post.return_value = response

        with pytest.raises(ValueError, match="not found"):
            fetcher.fetch_board("missing")

    def test_fetch_board_missing_data(self):
        """Missing board data raises ValueError."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()
        fetcher._create_visitor = MagicMock(return_value="visitor123")  # type: ignore

        response = MagicMock()
        response.json.return_value = {"data": {"board": None}}
        response.raise_for_status.return_value = None
        fetcher.client.post.return_value = response

        with pytest.raises(ValueError, match="No board data"):
            fetcher.fetch_board("board123")

    def test_fetch_board_http_status_error(self):
        """HTTP status errors are wrapped as ValueError."""
        fetcher = TaskCardsFetcher()
        fetcher.client = MagicMock()
        fetcher._create_visitor = MagicMock(return_value="visitor123")  # type: ignore

        error = httpx.HTTPStatusError(
            "fail",
            request=httpx.Request("POST", "https://example.com"),
            response=httpx.Response(404, request=httpx.Request("POST", "https://example.com")),
        )
        response = MagicMock()
        response.raise_for_status.side_effect = error
        fetcher.client.post.return_value = response

        with pytest.raises(ValueError, match="not found"):
            fetcher.fetch_board("board123")
