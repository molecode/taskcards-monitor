"""Command-line interface for TaskCards monitor."""

from importlib.metadata import version
from pathlib import Path

import click

from .display import (
    console,
    display_boards_list,
    display_changes,
    display_inspect_header,
    display_inspect_results,
    display_state,
)
from .email_notifier import EmailNotifier
from .fetcher import TaskCardsFetcher
from .monitor import BoardMonitor, BoardState


@click.group()
@click.version_option(version=version("taskcards-monitor"))
def main():
    """Monitor TaskCards boards for changes."""
    pass


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
            console.print(f"[dim]Previous state loaded from {monitor.state_file}[/dim]")
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

    # Find all state files
    state_files = sorted(state_dir.glob("*.json"))

    if not state_files:
        console.print(
            "[yellow]No boards have been checked yet.[/yellow]\n"
            "Run 'taskcards-monitor check BOARD_ID' to monitor your first board."
        )
        return

    # Load information from each state file using BoardMonitor
    boards_info = []
    for state_file in state_files:
        board_id = state_file.stem  # filename without .json extension
        monitor = BoardMonitor(board_id, state_dir=state_dir)
        state = monitor.get_previous_state()

        if state is None:
            # Skip invalid or corrupted state files
            continue

        boards_info.append(
            {
                "board_id": board_id,
                "board_name": state.board_name or "[dim]<unnamed>[/dim]",
                "timestamp": state.timestamp,
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


if __name__ == "__main__":
    main()
