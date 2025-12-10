"""Display utilities for TaskCards monitor output."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .monitor import BoardState

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
                f"[green]Initial state saved[/green]\nCards: {changes.get('cards_count', 0)}",
                title="First Run",
                border_style="green",
            )
        )
        return

    # Check if there are any changes
    has_changes = any(
        [
            changes.get("cards_added"),
            changes.get("cards_removed"),
            changes.get("cards_changed"),
        ]
    )

    if not has_changes:
        console.print(Panel("[dim]No changes detected[/dim]", title="Status", border_style="blue"))
        return

    # Display changes
    console.print("\n[bold green]Changes detected:[/bold green]\n")

    # Cards added
    if changes.get("cards_added"):
        table = create_table(
            "Cards Added",
            "bold green",
            [
                {"name": "Title", "style": "green"},
                {"name": "Description", "style": "green dim", "width": 50, "overflow": "fold"},
            ],
            [
                (
                    card.get("title", ""),
                    card.get("description") or "[dim]<empty>[/dim]",
                )
                for card in changes["cards_added"]
            ],
        )
        console.print(table)
        console.print()

    # Cards removed
    if changes.get("cards_removed"):
        table = create_table(
            "Cards Removed",
            "bold red",
            [
                {"name": "Title", "style": "red"},
                {"name": "Description", "style": "red dim", "width": 50, "overflow": "fold"},
            ],
            [
                (
                    card.get("title", ""),
                    card.get("description") or "[dim]<empty>[/dim]",
                )
                for card in changes["cards_removed"]
            ],
        )
        console.print(table)
        console.print()

    # Cards changed
    if changes.get("cards_changed"):
        rows = []
        for card in changes["cards_changed"]:
            # Determine what changed
            old_title = card.get("old_title", "")
            new_title = card.get("new_title", "")
            old_description = card.get("old_description", "")
            new_description = card.get("new_description", "")

            title_changed = old_title != new_title
            desc_changed = old_description != new_description

            if title_changed and desc_changed:
                change_type = "Title & Description"
            elif title_changed:
                change_type = "Title"
            else:
                change_type = "Description"

            old_desc = old_description or "[dim]<empty>[/dim]"
            new_desc = new_description or "[dim]<empty>[/dim]"

            rows.append(
                (
                    change_type,
                    old_title if title_changed else "[dim]unchanged[/dim]",
                    new_title if title_changed else "[dim]unchanged[/dim]",
                    old_desc if desc_changed else "[dim]unchanged[/dim]",
                    new_desc if desc_changed else "[dim]unchanged[/dim]",
                )
            )

        table = create_table(
            "Cards Changed",
            "bold yellow",
            [
                {"name": "Changed", "style": "yellow", "width": 15},
                {"name": "Old Title", "style": "dim", "width": 25, "overflow": "fold"},
                {"name": "New Title", "style": "yellow", "width": 25, "overflow": "fold"},
                {"name": "Old Description", "style": "dim", "width": 30, "overflow": "fold"},
                {"name": "New Description", "style": "yellow", "width": 30, "overflow": "fold"},
            ],
            rows,
        )
        console.print(table)
        console.print()


def display_state(state: BoardState) -> None:
    """Display the current board state."""

    console.print(f"\n[bold]Board State[/bold] (saved at {state.timestamp})\n")

    # Display cards
    if state.cards:
        table = create_table(
            "Cards",
            "bold magenta",
            [
                {"name": "Title", "style": "magenta", "width": 30},
                {"name": "Description", "style": "magenta dim", "width": 60, "overflow": "fold"},
            ],
            [
                (card_data["title"], card_data["description"] or "[dim]<empty>[/dim]")
                for _card_id, card_data in state.cards.items()
            ],
        )
        console.print(table)
        console.print()
    else:
        console.print("[dim]No cards found[/dim]\n")

    console.print(f"[dim]Total: {len(state.cards)} cards[/dim]\n")


def display_boards_list(boards_info: list[dict]) -> None:
    """Display a table of monitored boards."""

    console.print()
    table = create_table(
        f"Monitored Boards ({len(boards_info)} total)",
        "bold blue",
        [
            {"name": "Board ID", "style": "cyan"},
            {"name": "Last Checked", "style": "dim"},
            {"name": "Cards", "style": "magenta", "justify": "right"},
        ],
        [
            (
                board["board_id"],
                board["timestamp"],
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


def display_inspect_header(board_id: str) -> None:
    """Display header for inspect mode."""

    console.print(
        Panel(
            f"[bold cyan]Board ID:[/bold cyan] {board_id}\n"
            f"[dim]This is a debugging tool - state will NOT be saved[/dim]",
            title="Inspect Mode",
            border_style="cyan",
        )
    )


def display_inspect_results(state: BoardState) -> None:
    """Display results from board inspection."""

    console.print("\n[green]✓ Board loaded successfully![/green]\n")

    # Display detailed statistics
    console.print("[bold]Board Statistics:[/bold]")
    console.print(f"  Total Cards: {len(state.cards)}\n")

    # Display detailed card list
    if state.cards:
        table = create_table(
            "Cards",
            "bold magenta",
            [
                {"name": "Card Title", "style": "magenta", "width": 30, "overflow": "fold"},
                {
                    "name": "Description",
                    "style": "magenta dim",
                    "width": 60,
                    "overflow": "fold",
                },
            ],
            [
                (card_data["title"], card_data["description"] or "[dim]<empty>[/dim]")
                for _card_id, card_data in state.cards.items()
            ],
        )
        console.print(table)
        console.print()
    else:
        console.print("[dim]No cards found[/dim]\n")

    console.print(
        "[dim italic]Note: This inspection does not affect saved state or monitoring.[/dim italic]\n"
    )
