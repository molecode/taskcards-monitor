"""Fetcher for TaskCards board data using Playwright."""

from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# JavaScript to extract board data from DOM
EXTRACT_BOARD_DATA_JS = """
() => {
    const data = {
        lists: [],
        cards: []
    };

    // Find all card containers (each contains one list and its cards)
    const containers = document.querySelectorAll('.card-container');

    containers.forEach((container, listIndex) => {
        // Find the board-list (column header) within this container
        const listEl = container.querySelector('.board-list');
        if (!listEl) return;

        const listId = listEl.getAttribute('data-list-id') ||
                      listEl.getAttribute('id') ||
                      `list-${listIndex}`;

        // Find list title
        let listName = '';
        const headerEl = listEl.querySelector('.board-list-header');
        if (headerEl) {
            // Look for .text-h6 > .contenteditable
            const h6 = headerEl.querySelector('.text-h6');
            if (h6) {
                const editable = h6.querySelector('.contenteditable');
                if (editable) {
                    listName = editable.textContent.trim();
                }
            }
        }

        data.lists.push({
            id: listId,
            name: listName,
            position: listIndex,
            color: null
        });

        // Find the list-content-container (sibling of board-list)
        const contentContainer = container.querySelector('.list-content-container');
        if (!contentContainer) return;

        // Find all cards in this container
        const cards = contentContainer.querySelectorAll('.board-card');

        cards.forEach((cardEl, cardIndex) => {
            const cardId = cardEl.getAttribute('data-card-id') ||
                          cardEl.getAttribute('id') ||
                          `card-${listId}-${cardIndex}`;

            // Find card title from header
            let cardTitle = '';
            const cardHeader = cardEl.querySelector('.board-card-header');
            if (cardHeader) {
                const editable = cardHeader.querySelector('.contenteditable');
                if (editable) {
                    cardTitle = editable.textContent.trim();
                } else {
                    cardTitle = cardHeader.textContent.trim();
                }
            }

            // If no title found, use card content
            if (!cardTitle) {
                const cardContent = cardEl.querySelector('.board-card-content');
                if (cardContent) {
                    cardTitle = cardContent.textContent.trim().substring(0, 100);
                }
            }

            // Fallback to any text in the card
            if (!cardTitle) {
                cardTitle = cardEl.textContent.trim().substring(0, 100);
            }

            data.cards.push({
                id: cardId,
                title: cardTitle,
                description: '',
                created: null,
                modified: null,
                kanbanPosition: {
                    listId: listId,
                    position: cardIndex
                }
            });
        });
    });

    return data;
}
"""


class TaskCardsFetcher:
    """Fetches board data from TaskCards using browser automation."""

    def __init__(self, headless: bool = True, timeout: int = 60000):
        """
        Initialize the fetcher.

        Args:
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser = None

    def __enter__(self):
        """Context manager entry."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _fetch_board_internal(
        self,
        board_id: str,
        token: str | None = None,
        screenshot_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Internal method to fetch board data with optional screenshot.

        Args:
            board_id: The board ID
            token: Optional view token for private boards
            screenshot_path: Optional path to save screenshot

        Returns:
            Dictionary containing board data with lists and cards

        Raises:
            ValueError: If browser is not initialized or board data cannot be extracted
            PlaywrightTimeoutError: If page load times out
        """
        if not self.browser:
            raise ValueError("Browser not initialized. Use 'with' context manager.")

        # Construct URL
        base_url = f"https://www.taskcards.de/#/board/{board_id}/view"
        url = f"{base_url}?token={token}" if token else base_url

        # Create new page with viewport size
        page = self.browser.new_page(viewport={"width": 1920, "height": 1080})

        try:
            # Navigate to the board
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

            # Wait for lists to appear first
            page.wait_for_selector(".board-list", timeout=10000)

            # Wait a bit for cards to render
            page.wait_for_timeout(3000)

            # Try to wait for at least one card (some boards might have no cards)
            try:
                page.wait_for_selector(".board-card", timeout=5000)
            except Exception:  # noqa: S110
                # It's okay if there are no cards
                pass

            # Take screenshot if requested
            if screenshot_path:
                # Get the actual content dimensions to capture everything
                dimensions = page.evaluate("""
                    () => {
                        return {
                            width: Math.max(
                                document.documentElement.scrollWidth,
                                document.body.scrollWidth
                            ),
                            height: Math.max(
                                document.documentElement.scrollHeight,
                                document.body.scrollHeight
                            )
                        };
                    }
                """)
                # Set viewport to exact content dimensions (with reasonable max of 10000px)
                viewport_width = min(dimensions["width"], 10000)
                viewport_height = min(dimensions["height"], 10000)
                page.set_viewport_size({"width": viewport_width, "height": viewport_height})
                # Wait a moment for re-render after viewport change
                page.wait_for_timeout(1000)
                # Screenshot without full_page since viewport now contains everything
                page.screenshot(path=screenshot_path)

            # Extract board data from DOM
            board_data = page.evaluate(EXTRACT_BOARD_DATA_JS)

            # Validate we got board data
            if not board_data or (not board_data.get("lists") and not board_data.get("cards")):
                raise ValueError("Board data does not contain expected 'lists' or 'cards' fields")

            return board_data

        except PlaywrightTimeoutError as e:
            raise PlaywrightTimeoutError(
                f"Timeout while loading board {board_id}. "
                f"The board might not exist or be inaccessible."
            ) from e
        except Exception as e:
            # Try to get more context from the page
            try:
                page_content = page.content()
                if "404" in page_content or "not found" in page_content.lower():
                    raise ValueError(f"Board {board_id} not found") from e
                elif (
                    "access denied" in page_content.lower()
                    or "unauthorized" in page_content.lower()
                ):
                    raise ValueError(
                        f"Access denied to board {board_id}. "
                        f"Check if the board is private and requires a valid token."
                    ) from e
            except Exception:  # noqa: S110
                pass

            raise ValueError(f"Failed to extract board data: {str(e)}") from e

        finally:
            page.close()

    def fetch_board(self, board_id: str, token: str | None = None) -> dict[str, Any]:
        """
        Fetch board data using Playwright.

        Args:
            board_id: The board ID
            token: Optional view token for private boards

        Returns:
            Dictionary containing board data with lists and cards

        Raises:
            ValueError: If browser is not initialized or board data cannot be extracted
            PlaywrightTimeoutError: If page load times out
        """
        return self._fetch_board_internal(board_id, token)

    def fetch_board_with_screenshot(
        self, board_id: str, token: str | None = None, screenshot_path: str | None = None
    ) -> dict[str, Any]:
        """
        Fetch board data and optionally take a screenshot for debugging.

        Args:
            board_id: The board ID
            token: Optional view token for private boards
            screenshot_path: Optional path to save screenshot

        Returns:
            Dictionary containing board data
        """
        return self._fetch_board_internal(board_id, token, screenshot_path)
