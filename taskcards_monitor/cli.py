"""Command-line interface for TaskCards monitor."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .fetcher import TaskCardsFetcher
from .monitor import BoardMonitor, BoardState


console = Console()


def display_changes(changes: dict) -> None:
    """Display detected changes with beautiful formatting."""

    if changes.get("is_first_run"):
        console.print(
            Panel(
                f"[green]Initial state saved[/green]\n"
                f"Columns: {changes['columns_count']}\n"
                f"Cards: {changes['cards_count']}",
                title="First Run",
                border_style="green"
            )
        )
        return

    # Check if there are any changes
    has_changes = any([
        changes["columns_added"],
        changes["columns_removed"],
        changes["columns_renamed"],
        changes["cards_added"],
        changes["cards_removed"],
        changes["cards_moved"],
    ])

    if not has_changes:
        console.print(
            Panel(
                "[dim]No changes detected[/dim]",
                title="Status",
                border_style="blue"
            )
        )
        return

    # Display changes
    console.print("\n[bold green]Changes detected:[/bold green]\n")

    # Columns added
    if changes["columns_added"]:
        table = Table(title="Columns Added", show_header=True, header_style="bold green")
        table.add_column("Name", style="green")
        for col in changes["columns_added"]:
            table.add_row(col["name"])
        console.print(table)
        console.print()

    # Columns removed
    if changes["columns_removed"]:
        table = Table(title="Columns Removed", show_header=True, header_style="bold red")
        table.add_column("Name", style="red")
        for col in changes["columns_removed"]:
            table.add_row(col["name"])
        console.print(table)
        console.print()

    # Columns renamed
    if changes["columns_renamed"]:
        table = Table(title="Columns Renamed", show_header=True, header_style="bold yellow")
        table.add_column("Old Name", style="dim")
        table.add_column("New Name", style="yellow")
        for col in changes["columns_renamed"]:
            table.add_row(col["old_name"], col["new_name"])
        console.print(table)
        console.print()

    # Cards added
    if changes["cards_added"]:
        table = Table(title="Cards Added", show_header=True, header_style="bold green")
        table.add_column("Title", style="green")
        table.add_column("Column", style="dim")
        for card in changes["cards_added"]:
            table.add_row(card["title"], card["column"])
        console.print(table)
        console.print()

    # Cards removed
    if changes["cards_removed"]:
        table = Table(title="Cards Removed", show_header=True, header_style="bold red")
        table.add_column("Title", style="red")
        table.add_column("Column", style="dim")
        for card in changes["cards_removed"]:
            table.add_row(card["title"], card["column"])
        console.print(table)
        console.print()

    # Cards moved
    if changes["cards_moved"]:
        table = Table(title="Cards Moved", show_header=True, header_style="bold cyan")
        table.add_column("Title", style="cyan")
        table.add_column("From", style="dim")
        table.add_column("To", style="cyan")
        for card in changes["cards_moved"]:
            table.add_row(card["title"], card["from_column"], card["to_column"])
        console.print(table)
        console.print()


def display_state(state: BoardState) -> None:
    """Display the current board state."""

    console.print(f"\n[bold]Board State[/bold] (saved at {state.timestamp})\n")

    # Display columns
    if state.columns:
        table = Table(title="Columns", show_header=True, header_style="bold blue")
        table.add_column("Name", style="blue")
        table.add_column("Position", style="dim")
        for col_id, col_data in sorted(
            state.columns.items(),
            key=lambda x: x[1]["position"]
        ):
            table.add_row(col_data["name"], str(col_data["position"]))
        console.print(table)
        console.print()

    # Display cards
    if state.cards:
        table = Table(title="Cards", show_header=True, header_style="bold magenta")
        table.add_column("Title", style="magenta")
        table.add_column("Column", style="dim")
        for card_id, card_data in state.cards.items():
            column_name = state.columns.get(card_data["column_id"], {}).get("name", "Unknown")
            table.add_row(card_data["title"], column_name)
        console.print(table)
        console.print()

    console.print(
        f"[dim]Total: {len(state.columns)} columns, {len(state.cards)} cards[/dim]\n"
    )


@click.group()
@click.version_option(version="0.1.0")
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
        with console.status("[bold green]Fetching board data...", spinner="dots"):
            with TaskCardsFetcher(headless=headless) as fetcher:
                data = fetcher.fetch_board(board_id, token=token)

        if verbose:
            console.print("[dim]Board data fetched successfully[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()

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

    console.print(Panel(
        f"[bold cyan]Board ID:[/bold cyan] {board_id}\n"
        f"[dim]This is a debugging tool - state will NOT be saved[/dim]",
        title="Inspect Mode",
        border_style="cyan"
    ))

    try:
        console.print("\n[cyan]Opening browser (visible mode)...[/cyan]")

        with TaskCardsFetcher(headless=False) as fetcher:
            if screenshot:
                data = fetcher.fetch_board_with_screenshot(
                    board_id,
                    token=token,
                    screenshot_path=screenshot
                )
                console.print(f"\n[green]✓ Screenshot saved to:[/green] {screenshot}")
            else:
                data = fetcher.fetch_board(board_id, token=token)

        # Create state for display
        state = BoardState(data)

        console.print(f"\n[green]✓ Board loaded successfully![/green]\n")

        # Display detailed statistics
        console.print("[bold]Board Statistics:[/bold]")
        console.print(f"  Total Columns: {len(state.columns)}")
        console.print(f"  Total Cards: {len(state.cards)}")

        # Count cards per column
        cards_per_column = {}
        for card_id, card_data in state.cards.items():
            col_id = card_data["column_id"]
            cards_per_column[col_id] = cards_per_column.get(col_id, 0) + 1

        console.print(f"  Columns with cards: {len([c for c in cards_per_column.values() if c > 0])}")
        console.print(f"  Empty columns: {len(state.columns) - len([c for c in cards_per_column.values() if c > 0])}\n")

        # Display columns with card counts
        if state.columns:
            table = Table(title="Columns Overview", show_header=True, header_style="bold cyan")
            table.add_column("Position", style="dim", width=8)
            table.add_column("Column Name", style="cyan")
            table.add_column("Cards", style="green", justify="right", width=6)

            for col_id, col_data in sorted(
                state.columns.items(),
                key=lambda x: x[1]["position"]
            ):
                card_count = cards_per_column.get(col_id, 0)
                table.add_row(
                    str(col_data["position"]),
                    col_data["name"],
                    str(card_count)
                )
            console.print(table)
            console.print()

        # Display detailed card list
        if state.cards:
            table = Table(title="Cards Detail", show_header=True, header_style="bold magenta")
            table.add_column("Card Title", style="magenta", overflow="fold")
            table.add_column("Column", style="dim")
            table.add_column("Position", style="dim", justify="right", width=8)

            # Group cards by column and sort
            cards_by_column = {}
            for card_id, card_data in state.cards.items():
                col_id = card_data["column_id"]
                if col_id not in cards_by_column:
                    cards_by_column[col_id] = []
                cards_by_column[col_id].append((card_id, card_data))

            # Display cards sorted by column position then card position
            for col_id in sorted(state.columns.keys(), key=lambda x: state.columns[x]["position"]):
                if col_id in cards_by_column:
                    column_name = state.columns[col_id]["name"]
                    for card_id, card_data in sorted(cards_by_column[col_id], key=lambda x: x[1]["position"] or 0):
                        table.add_row(
                            card_data["title"][:60],
                            column_name,
                            str(card_data["position"] or "-")
                        )

            console.print(table)
            console.print()

        console.print("[dim italic]Note: This inspection does not affect saved state or monitoring.[/dim italic]\n")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()


if __name__ == "__main__":
    main()
