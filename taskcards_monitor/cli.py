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
    """Inspect a board and optionally save a screenshot for debugging."""

    console.print(f"[bold]Inspecting board:[/bold] {board_id}\n")

    try:
        with console.status("[bold green]Opening board in browser...", spinner="dots"):
            with TaskCardsFetcher(headless=False) as fetcher:
                if screenshot:
                    data = fetcher.fetch_board_with_screenshot(
                        board_id,
                        token=token,
                        screenshot_path=screenshot
                    )
                    console.print(f"[green]Screenshot saved to:[/green] {screenshot}")
                else:
                    data = fetcher.fetch_board(board_id, token=token)

        # Display basic info
        state = BoardState(data)
        console.print(f"\n[green]Board loaded successfully![/green]")
        console.print(f"Columns: {len(state.columns)}")
        console.print(f"Cards: {len(state.cards)}\n")

        # Display columns
        if state.columns:
            console.print("[bold]Columns:[/bold]")
            for col_id, col_data in sorted(
                state.columns.items(),
                key=lambda x: x[1]["position"]
            ):
                console.print(f"  • {col_data['name']}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()


if __name__ == "__main__":
    main()
