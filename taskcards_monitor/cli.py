"""Command-line interface for TaskCards monitor."""

from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import click

from .database import init_database
from .display import (
    console,
    display_boards_list,
    display_changes,
    display_history,
    display_inspect_header,
    display_inspect_results,
    display_state,
)
from .email_notifier import EmailNotifier
from .fetcher import TaskCardsFetcher
from .models import Board, Change
from .monitor import BoardMonitor, BoardState


@click.group()
@click.version_option(version=version("taskcards-monitor"))
def main():
    """Monitor TaskCards boards for changes."""
    # Initialize database on startup
    init_database()


@main.command()
@click.argument("board_id")
@click.option("--token", "-t", help="View token for private/protected boards")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option(
    "--email-config",
    "-e",
    type=click.Path(exists=True, path_type=Path),
    help="Path to email configuration YAML file",
)
def check(board_id: str, token: str | None, verbose: bool, email_config: Path | None):
    """Check a board for changes and log any differences."""

    if verbose:
        console.print(f"[dim]Checking board: {board_id}[/dim]")
        if token:
            console.print(f"[dim]Using view token: {token[:8]}...[/dim]")
        if email_config:
            console.print(f"[dim]Email notifications enabled: {email_config}[/dim]")

    # Initialize monitor
    monitor = BoardMonitor(board_id)

    # Get previous state
    previous_state = monitor.get_previous_state()

    if verbose:
        if previous_state:
            console.print("[dim]Previous state loaded from database[/dim]")
        else:
            console.print("[dim]No previous state found. This is the first run.[/dim]")

    # Fetch current board data
    try:
        with (
            console.status("[bold green]Fetching board data...", spinner="dots"),
            TaskCardsFetcher() as fetcher,
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

    # Send email notification if configured
    if email_config:
        try:
            if verbose:
                console.print("[dim]Sending email notification...[/dim]")

            notifier = EmailNotifier(email_config)
            email_sent = notifier.notify_changes(
                board_id=board_id,
                board_name=current_state.board_name,
                timestamp=current_state.timestamp,
                changes=changes,
                token=token,
            )

            if email_sent:
                console.print("[green]✓[/green] Email notification sent")
            elif verbose:
                console.print("[dim]No email sent (no changes or first run)[/dim]")

        except Exception as e:
            console.print(f"[bold red]Error sending email:[/bold red] {str(e)}")
            if verbose:
                import traceback

                console.print(f"[dim]{traceback.format_exc()}[/dim]")

    # Save current state
    monitor.save_state(current_state)

    if verbose:
        console.print("[dim]State saved to database[/dim]")


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
    # Get all boards from database
    boards = Board.select().order_by(Board.last_checked.desc())

    if not boards:
        console.print(
            "[yellow]No boards have been checked yet.[/yellow]\n"
            "Run 'taskcards-monitor check BOARD_ID' to monitor your first board."
        )
        return

    # Build boards info list
    boards_info = []
    for board in boards:
        monitor = BoardMonitor(board.board_id)
        state = monitor.get_previous_state()

        if state is None:
            # Skip boards without valid state (shouldn't happen)
            continue

        boards_info.append(
            {
                "board_id": board.board_id,
                "board_name": board.name or "[dim]<unnamed>[/dim]",
                "timestamp": board.last_checked.isoformat(),
                "cards": len(state.cards),
            }
        )

    if not boards_info:
        console.print("[yellow]No valid board states found.[/yellow]")
        return

    # Display the boards table
    display_boards_list(boards_info)


@main.command()
@click.argument("board_id")
@click.option("--token", "-t", help="View token for private/protected boards")
def inspect(board_id: str, token: str | None):
    """
    Inspect a board for debugging (detailed output).

    This command is for exploring and debugging boards. It:
    - Shows detailed information about all columns and cards
    - Does NOT save state or affect monitoring
    - Useful for verifying board access and structure
    """

    try:
        console.print("\n[cyan]Fetching board data...[/cyan]")

        with TaskCardsFetcher() as fetcher:
            data = fetcher.fetch_board(board_id, token=token)

        # Create state for display
        state = BoardState(data)

        # Display header with board name
        display_inspect_header(board_id, state.board_name or None)

        # Display results
        display_inspect_results(state)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e


@main.command()
@click.argument("board_id")
@click.option("--limit", "-n", type=int, default=20, help="Limit number of changes to display")
@click.option(
    "--since",
    help="Show changes since date (ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)",
)
@click.option("--card", help="Filter changes for a specific card ID")
def history(board_id: str, limit: int, since: str | None, card: str | None):
    """
    Show change history for a board.

    Displays a chronological log of all changes (added/removed/modified cards)
    detected for the specified board.

    Examples:
        taskcards-monitor history BOARD_ID
        taskcards-monitor history BOARD_ID --limit 50
        taskcards-monitor history BOARD_ID --since 2025-12-01
        taskcards-monitor history BOARD_ID --card CARD_ID
    """
    # Get board
    board = Board.get_or_none(Board.board_id == board_id)
    if not board:
        console.print(
            f"[yellow]No history found for board {board_id}[/yellow]\n"
            f"Run 'taskcards-monitor check {board_id}' to start monitoring."
        )
        return

    # Build query
    query = Change.select().where(Change.board == board)

    if since:
        try:
            # Try parsing with time first, then just date
            try:
                since_dt = datetime.fromisoformat(since)
            except ValueError:
                since_dt = datetime.fromisoformat(f"{since} 00:00:00")
            query = query.where(Change.timestamp >= since_dt)
        except ValueError:
            console.print(
                f"[red]Invalid date format:[/red] {since}\n"
                "Use ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
            )
            return

    if card:
        query = query.where(Change.card_id == card)

    query = query.order_by(Change.timestamp.desc()).limit(limit)

    changes = list(query)

    # Display history using display module
    display_history(board.name or board_id, changes)


if __name__ == "__main__":
    main()
