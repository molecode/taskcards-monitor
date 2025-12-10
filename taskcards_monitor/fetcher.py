"""Fetcher for TaskCards board data using GraphQL API."""

from typing import Any

import httpx


class TaskCardsFetcher:
    """Fetches board data from TaskCards using GraphQL API."""

    BASE_URL = "https://www.taskcards.de"
    GRAPHQL_URL = f"{BASE_URL}/graphql"

    # GraphQL query for fetching complete board data
    BOARD_QUERY = """
    query ($id: String!) {
      board(id: $id) {
        id
        name
        description
        lists {
          id
          name
          position
          color
        }
        cards {
          id
          title
          description
          created
          modified
          kanbanPosition {
            listId
            position
          }
        }
      }
    }
    """

    def __init__(self, headless: bool = True, timeout: int = 60):
        """
        Initialize the fetcher.

        Args:
            headless: Unused (kept for backwards compatibility)
            timeout: Request timeout in seconds (default: 60)
        """
        self.timeout = timeout
        self.client: httpx.Client | None = None
        self.x_token: str | None = None

    def __enter__(self):
        """Context manager entry."""
        self.client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.client:
            self.client.close()

    def _create_visitor(self) -> str:
        """
        Create a visitor session and return the x-token.

        Returns:
            str: Visitor ID to use as x-token for authenticated requests

        Raises:
            ValueError: If visitor creation fails
        """
        if not self.client:
            raise ValueError("Client not initialized. Use 'with' context manager.")

        mutation = "mutation { createVisitor { id noActive } }"

        try:
            response = self.client.post(
                self.GRAPHQL_URL,
                json={"query": mutation},
            )
            response.raise_for_status()

            data = response.json()
            visitor_id = data.get("data", {}).get("createVisitor", {}).get("id")

            if not visitor_id:
                raise ValueError("Failed to get visitor ID from response")

            return visitor_id

        except httpx.HTTPError as e:
            raise ValueError(f"Failed to create visitor: {e}") from e

    def _grant_access(self, board_id: str, view_token: str) -> None:
        """
        Grant access to a private board using the view token.

        Args:
            board_id: The board ID
            view_token: The view token for the board

        Raises:
            ValueError: If access cannot be granted
        """
        if not self.client or not self.x_token:
            raise ValueError("Client or x-token not initialized")

        url = f"{self.BASE_URL}/api/boards/{board_id}/permissions/{view_token}/accesses"

        try:
            response = self.client.post(
                url,
                headers={"x-token": self.x_token},
                json={"password": ""},
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Board {board_id} not found or view token is invalid") from e
            elif e.response.status_code in (401, 403):
                raise ValueError(
                    f"Access denied to board {board_id}. Check your view token."
                ) from e
            else:
                raise ValueError(f"Failed to grant access: {e}") from e
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to grant access: {e}") from e

    def fetch_board(
        self,
        board_id: str,
        token: str | None = None,
        screenshot_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch board data using GraphQL API.

        Args:
            board_id: The board ID
            token: Optional view token for private boards
            screenshot_path: Unused (kept for backwards compatibility)

        Returns:
            Dictionary containing board data with lists and cards

        Raises:
            ValueError: If board cannot be fetched or data is invalid
        """
        if not self.client:
            raise ValueError("Client not initialized. Use 'with' context manager.")

        if screenshot_path:
            # Screenshots are not supported with API-based fetching
            # Could be implemented later with a separate browser automation step
            pass

        # Step 1: Create visitor and get x-token
        self.x_token = self._create_visitor()

        # Step 2: Grant access if view token is provided
        if token:
            self._grant_access(board_id, token)

        # Step 3: Fetch board data
        try:
            response = self.client.post(
                self.GRAPHQL_URL,
                headers={"x-token": self.x_token},
                json={
                    "variables": {"id": board_id},
                    "query": self.BOARD_QUERY,
                },
            )
            response.raise_for_status()

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                errors = data["errors"]
                error_msg = errors[0].get("message", "Unknown error")
                error_code = errors[0].get("extensions", {}).get("code", "")

                if error_code == "BOARD_ERROR":
                    raise ValueError(
                        f"Board {board_id} not found or you don't have access. "
                        f"For private boards, provide a valid view token."
                    )
                else:
                    raise ValueError(f"GraphQL error: {error_msg}")

            # Extract board data
            board_data = data.get("data", {}).get("board")

            if not board_data:
                raise ValueError("No board data in response")

            # Return in the expected format (with lists and cards at top level)
            return {
                "lists": board_data.get("lists", []),
                "cards": board_data.get("cards", []),
                "board": board_data,  # Include full board data for future use
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Board {board_id} not found") from e
            else:
                raise ValueError(f"Failed to fetch board: {e}") from e
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to fetch board: {e}") from e
