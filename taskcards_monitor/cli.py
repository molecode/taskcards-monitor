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
                f"[green]Initial state saved[/green]\nCards: {changes['cards_count']}",
                title="First Run",
                border_style="green",
            )
        )
        return

    # Check if there are any changes
    has_changes = any(
        [
            changes["cards_added"],
            changes["cards_removed"],
            changes["cards_changed"],
        ]
    )

    if not has_changes:
        console.print(Panel("[dim]No changes detected[/dim]", title="Status", border_style="blue"))
        return

    # Display changes
    console.print("\n[bold green]Changes detected:[/bold green]\n")

    # Cards added
    if changes["cards_added"]:
        # Show title and description for added cards
        for card in changes["cards_added"]:
            console.print(
                Panel(
                    f"[bold green]{card['title']}[/bold green]\n\n{card['description'] or '[dim]No description[/dim]'}",
                    title="Card Added",
                    border_style="green",
                )
            )
            console.print()

    # Cards removed
    if changes["cards_removed"]:
        # Show title and description for removed cards
        for card in changes["cards_removed"]:
            console.print(
                Panel(
                    f"[bold red]{card['title']}[/bold red]\n\n{card['description'] or '[dim]No description[/dim]'}",
                    title="Card Removed",
                    border_style="red",
                )
            )
            console.print()

    # Cards changed
    if changes["cards_changed"]:
        # Show title/description changes
        for card in changes["cards_changed"]:
            title_changed = card["old_title"] != card["new_title"]
            desc_changed = card["old_description"] != card["new_description"]

            content = ""
            if title_changed:
                content += "[bold]Title:[/bold]\n"
                content += f"[dim]- {card['old_title']}[/dim]\n"
                content += f"[green]+ {card['new_title']}[/green]\n\n"

            if desc_changed:
                content += "[bold]Description:[/bold]\n"
                content += f"[dim]- {card['old_description'] or '(empty)'}[/dim]\n"
                content += f"[green]+ {card['new_description'] or '(empty)'}[/green]"

            console.print(
                Panel(
                    content.strip(),
                    title="Card Changed",
                    border_style="yellow",
                )
            )
            console.print()


def display_state(state: BoardState) -> None:
    """Display the current board state."""

    console.print(f"\n[bold]Board State[/bold] (saved at {state.timestamp})\n")

    # Display cards
    if state.cards:
        console.print(f"[bold]Total Cards:[/bold] {len(state.cards)}\n")
        for card_id, card_data in state.cards.items():
            console.print(
                Panel(
                    f"[bold]{card_data['title']}[/bold]\n\n{card_data['description'] or '[dim]No description[/dim]'}",
                    title=f"Card: {card_id}",
                    border_style="magenta",
                )
            )
            console.print()
    else:
        console.print("[dim]No cards found[/dim]\n")


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


@main.command(name="list")
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
        console.print(f"  Total Cards: {len(state.cards)}\n")

        # Display detailed card list
        if state.cards:
            console.print(f"[bold]Cards ({len(state.cards)} total):[/bold]\n")
            for card_id, card_data in state.cards.items():
                console.print(
                    Panel(
                        f"[bold]{card_data['title']}[/bold]\n\n{card_data['description'] or '[dim]No description[/dim]'}",
                        title=f"Card: {card_id}",
                        border_style="magenta",
                    )
                )
                console.print()
        else:
            console.print("[dim]No cards found[/dim]\n")

        console.print(
            "[dim italic]Note: This inspection does not affect saved state or monitoring.[/dim italic]\n"
        )

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e


if __name__ == "__main__":
    main()
