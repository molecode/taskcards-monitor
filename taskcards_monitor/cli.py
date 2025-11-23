"""Command-line interface for TaskCards monitor."""

import json
from importlib.metadata import version
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .fetcher import TaskCardsFetcher
from .monitor import BoardMonitor, BoardState

console = Console()


def create_table(title: str, header_style: str, columns: list[dict], rows: list) -> Table:
    """Create a Rich table with the given configuration.

    Args:
        title: Table title
        header_style: Style for table headers
        columns: List of column configs with 'name', 'style', etc.
        rows: List of row data (tuples/lists matching column count)

    Returns:
        Configured Rich Table
    """
    table = Table(title=title, show_header=True, header_style=header_style)
    for col in columns:
        table.add_column(
            col["name"],
            style=col.get("style", ""),
            width=col.get("width"),
            justify=col.get("justify", "left"),
            overflow=col.get("overflow", "ellipsis"),
        )
    for row in rows:
        table.add_row(*row)
    return table


def display_changes(changes: dict) -> None:
    """Display detected changes with beautiful formatting."""

    if changes.get("is_first_run"):
        console.print(
            Panel(
                f"[green]Initial state saved[/green]\n"
                f"Columns: {changes['columns_count']}\n"
                f"Cards: {changes['cards_count']}",
                title="First Run",
                border_style="green",
            )
        )
        return

    # Check if there are any changes
    has_changes = any(
        [
            changes["columns_added"],
            changes["columns_removed"],
            changes["columns_renamed"],
            changes["cards_added"],
            changes["cards_removed"],
            changes["cards_moved"],
        ]
    )

    if not has_changes:
        console.print(Panel("[dim]No changes detected[/dim]", title="Status", border_style="blue"))
        return

    # Display changes
    console.print("\n[bold green]Changes detected:[/bold green]\n")

    # Columns added
    if changes["columns_added"]:
        table = create_table(
            "Columns Added",
            "bold green",
            [{"name": "Name", "style": "green"}],
            [(col["name"],) for col in changes["columns_added"]],
        )
        console.print(table)
        console.print()

    # Columns removed
    if changes["columns_removed"]:
        table = create_table(
            "Columns Removed",
            "bold red",
            [{"name": "Name", "style": "red"}],
            [(col["name"],) for col in changes["columns_removed"]],
        )
        console.print(table)
        console.print()

    # Columns renamed
    if changes["columns_renamed"]:
        table = create_table(
            "Columns Renamed",
            "bold yellow",
            [{"name": "Old Name", "style": "dim"}, {"name": "New Name", "style": "yellow"}],
            [(col["old_name"], col["new_name"]) for col in changes["columns_renamed"]],
        )
        console.print(table)
        console.print()

    # Cards added
    if changes["cards_added"]:
        table = create_table(
            "Cards Added",
            "bold green",
            [{"name": "Title", "style": "green"}, {"name": "Column", "style": "dim"}],
            [(card["title"], card["column"]) for card in changes["cards_added"]],
        )
        console.print(table)
        console.print()

    # Cards removed
    if changes["cards_removed"]:
        table = create_table(
            "Cards Removed",
            "bold red",
            [{"name": "Title", "style": "red"}, {"name": "Column", "style": "dim"}],
            [(card["title"], card["column"]) for card in changes["cards_removed"]],
        )
        console.print(table)
        console.print()

    # Cards moved
    if changes["cards_moved"]:
        table = create_table(
            "Cards Moved",
            "bold cyan",
            [
                {"name": "Title", "style": "cyan"},
                {"name": "From", "style": "dim"},
                {"name": "To", "style": "cyan"},
            ],
            [
                (card["title"], card["from_column"], card["to_column"])
                for card in changes["cards_moved"]
            ],
        )
        console.print(table)
        console.print()


def display_state(state: BoardState) -> None:
    """Display the current board state."""

    console.print(f"\n[bold]Board State[/bold] (saved at {state.timestamp})\n")

    # Display columns
    if state.columns:
        table = create_table(
            "Columns",
            "bold blue",
            [{"name": "Name", "style": "blue"}, {"name": "Position", "style": "dim"}],
            [
                (col_data["name"], str(col_data["position"]))
                for _col_id, col_data in sorted(
                    state.columns.items(), key=lambda x: x[1]["position"]
                )
            ],
        )
        console.print(table)
        console.print()

    # Display cards
    if state.cards:
        table = create_table(
            "Cards",
            "bold magenta",
            [{"name": "Title", "style": "magenta"}, {"name": "Column", "style": "dim"}],
            [
                (
                    card_data["title"],
                    state.columns.get(card_data["column_id"], {}).get("name", "Unknown"),
                )
                for _card_id, card_data in state.cards.items()
            ],
        )
        console.print(table)
        console.print()

    console.print(f"[dim]Total: {len(state.columns)} columns, {len(state.cards)} cards[/dim]\n")


@click.group()
@click.version_option(version=version("taskcards-monitor"))
def main():
    """Monitor TaskCards boards for changes."""
    pass


@main.command()
@click.argument("board_id")
@click.option("--token", "-t", help="View token for private/protected boards")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
def check(board_id: str, token: str | None, headless: bool, verbose: bool):
    """Check a board for changes and log any differences."""

    if verbose:
        console.print(f"[dim]Checking board: {board_id}[/dim]")
        if token:
            console.print(f"[dim]Using view token: {token[:8]}...[/dim]")

    # Initialize monitor
    monitor = BoardMonitor(board_id)

    # Get previous state
    previous_state = monitor.get_previous_state()

    if verbose:
        if previous_state:
            console.print(f"[dim]Previous state loaded from {monitor.state_file}[/dim]")
        else:
            console.print("[dim]No previous state found. This is the first run.[/dim]")

    # Fetch current board data
    try:
        with (
            console.status("[bold green]Fetching board data...", spinner="dots"),
            TaskCardsFetcher(headless=headless) as fetcher,
        ):
            data = fetcher.fetch_board(board_id, token=token)

        if verbose:
            console.print("[dim]Board data fetched successfully[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e

    # Create current state
    current_state = BoardState(data)

    # Detect changes
    changes = monitor.detect_changes(current_state, previous_state)

    # Display changes
    display_changes(changes)

    # Save current state
    monitor.save_state(current_state)

    if verbose:
        console.print(f"[dim]State saved to {monitor.state_file}[/dim]")


@main.command()
@click.argument("board_id")
def show(board_id: str):
    """Show the current saved state of a board."""

    monitor = BoardMonitor(board_id)
    state = monitor.get_previous_state()

    if state is None:
        console.print(
            f"[yellow]No saved state found for board {board_id}[/yellow]\n"
            f"Run 'taskcards-monitor check {board_id}' first."
        )
        return

    display_state(state)


@main.command()
def list_boards():
    """List all boards that have been checked."""

    # Get the state directory (same logic as BoardMonitor.__init__)
    state_dir = Path.home() / ".cache" / "taskcards-monitor"

    if not state_dir.exists():
        console.print(
            "[yellow]No boards have been checked yet.[/yellow]\n"
            "Run 'taskcards-monitor check BOARD_ID' to monitor your first board."
        )
        return

    # Find all state files
    state_files = sorted(state_dir.glob("*.json"))

    if not state_files:
        console.print(
            "[yellow]No boards have been checked yet.[/yellow]\n"
            "Run 'taskcards-monitor check BOARD_ID' to monitor your first board."
        )
        return

    # Load information from each state file
    boards_info = []
    for state_file in state_files:
        board_id = state_file.stem  # filename without .json extension
        try:
            with open(state_file) as f:
                data = json.load(f)
                timestamp = data.get("timestamp", "Unknown")
                columns_count = len(data.get("columns", {}))
                cards_count = len(data.get("cards", {}))

                boards_info.append(
                    {
                        "board_id": board_id,
                        "timestamp": timestamp,
                        "columns": columns_count,
                        "cards": cards_count,
                    }
                )
        except (json.JSONDecodeError, KeyError):
            # Skip malformed files
            continue

    if not boards_info:
        console.print("[yellow]No valid board states found.[/yellow]")
        return

    # Display the boards table
    console.print()
    table = create_table(
        f"Monitored Boards ({len(boards_info)} total)",
        "bold blue",
        [
            {"name": "Board ID", "style": "cyan"},
            {"name": "Last Checked", "style": "dim"},
            {"name": "Columns", "style": "green", "justify": "right"},
            {"name": "Cards", "style": "magenta", "justify": "right"},
        ],
        [
            (
                board["board_id"],
                board["timestamp"],
                str(board["columns"]),
                str(board["cards"]),
            )
            for board in boards_info
        ],
    )
    console.print(table)
    console.print()
    console.print(
        "[dim]Tip: Use 'taskcards-monitor show BOARD_ID' to see detailed state for a specific board[/dim]\n"
    )


@main.command()
@click.argument("board_id")
@click.option("--token", "-t", help="View token for private/protected boards")
@click.option("--screenshot", "-s", help="Save screenshot to this path")
def inspect(board_id: str, token: str | None, screenshot: str | None):
    """
    Inspect a board for debugging (visible browser, detailed output).

    This command is for exploring and debugging boards. It:
    - Always opens a visible browser window
    - Shows detailed information about all columns and cards
    - Does NOT save state or affect monitoring
    - Keeps browser open briefly for manual inspection
    """

    console.print(
        Panel(
            f"[bold cyan]Board ID:[/bold cyan] {board_id}\n"
            f"[dim]This is a debugging tool - state will NOT be saved[/dim]",
            title="Inspect Mode",
            border_style="cyan",
        )
    )

    try:
        console.print("\n[cyan]Opening browser (visible mode)...[/cyan]")

        with TaskCardsFetcher(headless=False) as fetcher:
            data = fetcher.fetch_board(board_id, token=token, screenshot_path=screenshot)
            if screenshot:
                console.print(f"\n[green]✓ Screenshot saved to:[/green] {screenshot}")

        # Create state for display
        state = BoardState(data)

        console.print("\n[green]✓ Board loaded successfully![/green]\n")

        # Display detailed statistics
        console.print("[bold]Board Statistics:[/bold]")
        console.print(f"  Total Columns: {len(state.columns)}")
        console.print(f"  Total Cards: {len(state.cards)}")

        # Count cards per column
        cards_per_column = {}
        for _card_id, card_data in state.cards.items():
            col_id = card_data["column_id"]
            cards_per_column[col_id] = cards_per_column.get(col_id, 0) + 1

        console.print(
            f"  Columns with cards: {len([c for c in cards_per_column.values() if c > 0])}"
        )
        console.print(
            f"  Empty columns: {len(state.columns) - len([c for c in cards_per_column.values() if c > 0])}\n"
        )

        # Display columns with card counts
        if state.columns:
            table = create_table(
                "Columns Overview",
                "bold cyan",
                [
                    {"name": "Position", "style": "dim", "width": 8},
                    {"name": "Column Name", "style": "cyan"},
                    {"name": "Cards", "style": "green", "justify": "right", "width": 6},
                ],
                [
                    (
                        str(col_data["position"]),
                        col_data["name"],
                        str(cards_per_column.get(col_id, 0)),
                    )
                    for col_id, col_data in sorted(
                        state.columns.items(), key=lambda x: x[1]["position"]
                    )
                ],
            )
            console.print(table)
            console.print()

        # Display detailed card list
        if state.cards:
            # Group cards by column and sort
            cards_by_column = {}
            for card_id, card_data in state.cards.items():
                col_id = card_data["column_id"]
                if col_id not in cards_by_column:
                    cards_by_column[col_id] = []
                cards_by_column[col_id].append((card_id, card_data))

            # Build rows sorted by column position then card position
            rows = []
            for col_id in sorted(state.columns.keys(), key=lambda x: state.columns[x]["position"]):
                if col_id in cards_by_column:
                    column_name = state.columns[col_id]["name"]
                    for _card_id, card_data in sorted(
                        cards_by_column[col_id], key=lambda x: x[1]["position"] or 0
                    ):
                        rows.append(
                            (
                                card_data["title"][:60],
                                column_name,
                                str(card_data["position"] or "-"),
                            )
                        )

            table = create_table(
                "Cards Detail",
                "bold magenta",
                [
                    {"name": "Card Title", "style": "magenta", "overflow": "fold"},
                    {"name": "Column", "style": "dim"},
                    {"name": "Position", "style": "dim", "justify": "right", "width": 8},
                ],
                rows,
            )
            console.print(table)
            console.print()

        console.print(
            "[dim italic]Note: This inspection does not affect saved state or monitoring.[/dim italic]\n"
        )

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e


if __name__ == "__main__":
    main()
