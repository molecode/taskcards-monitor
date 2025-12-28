"""Display utilities for TaskCards monitor output."""

import json

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


def _format_link(link: str) -> str:
    """Format link for display in terminal."""
    if not link:
        return "[dim]<none>[/dim]"
    return link


def _format_attachments(attachments: list) -> str:
    """Format attachments for display in terminal."""
    if not attachments:
        return "[dim]<none>[/dim]"
    return (
        f"{len(attachments)} file(s): "
        + ", ".join(att.get("filename", "<unknown>") for att in attachments[:3])
        + (" ..." if len(attachments) > 3 else "")
    )


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
                {"name": "Title", "style": "green", "width": 20, "overflow": "fold"},
                {"name": "Description", "style": "green dim", "width": 25, "overflow": "fold"},
                {"name": "Link", "style": "blue", "width": 25, "overflow": "fold"},
                {"name": "Column", "style": "cyan", "width": 12},
                {"name": "Attachments", "style": "magenta", "width": 30, "overflow": "fold"},
            ],
            [
                (
                    card.get("title", ""),
                    card.get("description") or "[dim]<empty>[/dim]",
                    _format_link(card.get("link", "")),
                    card.get("column") or "[dim]<unknown>[/dim]",
                    _format_attachments(card.get("attachments", [])),
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
                {"name": "Title", "style": "red", "width": 20, "overflow": "fold"},
                {"name": "Description", "style": "red dim", "width": 25, "overflow": "fold"},
                {"name": "Link", "style": "blue", "width": 25, "overflow": "fold"},
                {"name": "Column", "style": "cyan", "width": 12},
                {"name": "Attachments", "style": "magenta", "width": 30, "overflow": "fold"},
            ],
            [
                (
                    card.get("title", ""),
                    card.get("description") or "[dim]<empty>[/dim]",
                    _format_link(card.get("link", "")),
                    card.get("column") or "[dim]<unknown>[/dim]",
                    _format_attachments(card.get("attachments", [])),
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
            old_link = card.get("old_link", "")
            new_link = card.get("new_link", "")
            old_column = card.get("old_column", "")
            new_column = card.get("new_column", "")
            attachments_added = card.get("attachments_added", [])
            attachments_removed = card.get("attachments_removed", [])

            title_changed = old_title != new_title
            desc_changed = old_description != new_description
            link_changed = old_link != new_link
            column_changed = old_column != new_column
            attachments_changed = bool(attachments_added or attachments_removed)

            # Build change type string
            changes_list = []
            if title_changed:
                changes_list.append("Title")
            if desc_changed:
                changes_list.append("Description")
            if link_changed:
                changes_list.append("Link")
            if column_changed:
                changes_list.append("Column")
            if attachments_changed:
                changes_list.append("Attachments")

            change_type = " & ".join(changes_list) if changes_list else "Unknown"

            old_desc = old_description or "[dim]<empty>[/dim]"
            new_desc = new_description or "[dim]<empty>[/dim]"
            old_col = old_column or "[dim]<unknown>[/dim]"
            new_col = new_column or "[dim]<unknown>[/dim]"

            # Format attachment changes
            attachment_change = ""
            if attachments_added and attachments_removed:
                attachment_change = (
                    f"[green]+{len(attachments_added)}[/green] / "
                    f"[red]-{len(attachments_removed)}[/red]"
                )
            elif attachments_added:
                attachment_change = (
                    f"[green]+{len(attachments_added)}[/green]: "
                    + ", ".join(att.get("filename", "<unknown>") for att in attachments_added[:2])
                    + (" ..." if len(attachments_added) > 2 else "")
                )
            elif attachments_removed:
                attachment_change = (
                    f"[red]-{len(attachments_removed)}[/red]: "
                    + ", ".join(att.get("filename", "<unknown>") for att in attachments_removed[:2])
                    + (" ..." if len(attachments_removed) > 2 else "")
                )
            else:
                attachment_change = "[dim]unchanged[/dim]"

            rows.append(
                (
                    change_type,
                    old_title if title_changed else "[dim]unchanged[/dim]",
                    new_title if title_changed else "[dim]unchanged[/dim]",
                    old_desc if desc_changed else "[dim]unchanged[/dim]",
                    new_desc if desc_changed else "[dim]unchanged[/dim]",
                    _format_link(old_link) if link_changed else "[dim]unchanged[/dim]",
                    _format_link(new_link) if link_changed else "[dim]unchanged[/dim]",
                    old_col if column_changed else "[dim]unchanged[/dim]",
                    new_col,
                    attachment_change,
                )
            )

        table = create_table(
            "Cards Changed",
            "bold yellow",
            [
                {"name": "Changed", "style": "yellow", "width": 12},
                {"name": "Old Title", "style": "dim", "width": 12, "overflow": "fold"},
                {"name": "New Title", "style": "yellow", "width": 12, "overflow": "fold"},
                {"name": "Old Desc", "style": "dim", "width": 12, "overflow": "fold"},
                {"name": "New Desc", "style": "yellow", "width": 12, "overflow": "fold"},
                {"name": "Old Link", "style": "dim", "width": 15, "overflow": "fold"},
                {"name": "New Link", "style": "blue", "width": 15, "overflow": "fold"},
                {"name": "Old Column", "style": "dim", "width": 10},
                {"name": "New Column", "style": "cyan", "width": 10},
                {"name": "Attachments", "style": "magenta", "width": 20, "overflow": "fold"},
            ],
            rows,
        )
        console.print(table)
        console.print()


def _display_board_details(state: BoardState) -> None:
    """Display columns and cards for a board state (reusable helper)."""

    # Display columns/lists
    if state.lists:
        # Count cards per column
        full_cards = state.data.get("cards", [])
        card_count_by_list = {}
        for card in full_cards:
            kanban_pos = card.get("kanbanPosition", {})
            list_id = kanban_pos.get("listId") if kanban_pos else None
            if list_id:
                card_count_by_list[list_id] = card_count_by_list.get(list_id, 0) + 1

        table = create_table(
            "Columns",
            "bold cyan",
            [
                {"name": "Column Name", "style": "cyan", "width": 40},
                {"name": "Position", "style": "cyan dim", "justify": "right", "width": 10},
                {"name": "Cards", "style": "cyan", "justify": "right", "width": 10},
            ],
            [
                (
                    lst.get("name", "[dim]<unnamed>[/dim]"),
                    str(lst.get("position", 0)),
                    str(card_count_by_list.get(lst.get("id"), 0)),
                )
                for lst in sorted(state.lists, key=lambda x: x.get("position", 0))
            ],
        )
        console.print(table)
        console.print()

    # Create a mapping of list_id to list name for quick lookup
    list_name_map = {lst.get("id"): lst.get("name", "[dim]<unnamed>[/dim]") for lst in state.lists}

    # Display cards with column information
    full_cards = state.data.get("cards", [])
    if full_cards:
        rows = []
        for card in full_cards:
            title = card.get("title", "[dim]<untitled>[/dim]")
            description = card.get("description", "") or "[dim]<empty>[/dim]"
            link = card.get("link", "")
            attachments = card.get("attachments", [])
            kanban_pos = card.get("kanbanPosition", {})
            list_id = kanban_pos.get("listId") if kanban_pos else None
            column_name = (
                list_name_map.get(list_id, "[dim]<unknown>[/dim]")
                if list_id
                else "[dim]<no column>[/dim]"
            )
            rows.append(
                (
                    title,
                    column_name,
                    description,
                    _format_link(link),
                    _format_attachments(attachments),
                )
            )

        table = create_table(
            "Cards",
            "bold magenta",
            [
                {"name": "Card Title", "style": "magenta", "width": 25, "overflow": "fold"},
                {"name": "Column", "style": "cyan", "width": 18},
                {
                    "name": "Description",
                    "style": "magenta dim",
                    "width": 25,
                    "overflow": "fold",
                },
                {"name": "Link", "style": "blue", "width": 25, "overflow": "fold"},
                {"name": "Attachments", "style": "green", "width": 25, "overflow": "fold"},
            ],
            rows,
        )
        console.print(table)
        console.print()
    else:
        console.print("[dim]No cards found[/dim]\n")


def display_state(state: BoardState) -> None:
    """Display the current board state."""

    header = "[bold]Board State[/bold]"
    if state.board_name:
        header += f" - {state.board_name}"
    header += f" (saved at {state.timestamp})"
    console.print(f"\n{header}\n")

    _display_board_details(state)

    console.print(f"[dim]Total: {len(state.cards)} cards[/dim]\n")


def display_boards_list(boards_info: list[dict]) -> None:
    """Display a table of monitored boards."""

    console.print()
    table = create_table(
        f"Monitored Boards ({len(boards_info)} total)",
        "bold blue",
        [
            {"name": "Board ID", "style": "cyan"},
            {"name": "Board Name", "style": "bold"},
            {"name": "Last Checked", "style": "dim"},
            {"name": "Cards", "style": "magenta", "justify": "right"},
        ],
        [
            (
                board["board_id"],
                board.get("board_name", "[dim]<unnamed>[/dim]"),
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


def display_inspect_header(board_id: str, board_name: str | None = None) -> None:
    """Display header for inspect mode."""

    header_content = f"[bold cyan]Board ID:[/bold cyan] {board_id}\n"
    if board_name:
        header_content += f"[bold]Board Name:[/bold] {board_name}\n"
    header_content += "[dim]This is a debugging tool - state will NOT be saved[/dim]"

    console.print(
        Panel(
            header_content,
            title="Inspect Mode",
            border_style="cyan",
        )
    )


def display_inspect_results(state: BoardState) -> None:
    """Display results from board inspection."""

    console.print("\n[green]✓ Board loaded successfully![/green]\n")

    # Display detailed statistics
    console.print("[bold]Board Statistics:[/bold]")
    console.print(f"  Total Columns: {len(state.lists)}")
    console.print(f"  Total Cards: {len(state.cards)}\n")

    _display_board_details(state)

    console.print(
        "[dim italic]Note: This inspection does not affect saved state or monitoring.[/dim italic]\n"
    )


def display_history(board_name: str, changes: list) -> None:
    """
    Display change history for a board.

    Args:
        board_name: Name of the board
        changes: List of Change model instances
    """
    if not changes:
        console.print(f"[yellow]No changes found for board {board_name}[/yellow]")
        return

    # Display header
    console.print(f"\n[bold cyan]Change History:[/bold cyan] {board_name}")
    console.print(f"[dim]Showing {len(changes)} most recent changes[/dim]\n")

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Timestamp", style="dim", width=19)
    table.add_column("Type", width=12)
    table.add_column("Card ID", style="cyan", width=36)
    table.add_column("Details", overflow="fold")

    # Add rows
    for change in changes:
        # Parse details JSON
        details = json.loads(change.details)

        # Format change type
        type_styles = {
            "card_added": "[green]Added[/green]",
            "card_removed": "[red]Removed[/red]",
            "card_modified": "[yellow]Modified[/yellow]",
            "card_moved": "[blue]Moved[/blue]",
        }
        change_type = type_styles.get(change.change_type, change.change_type)

        # Format details based on type
        if change.change_type == "card_added":
            detail_text = f"[green]+[/green] {details.get('title', 'Untitled')}"
            if details.get("column"):
                detail_text += f" → {details['column']}"

        elif change.change_type == "card_removed":
            detail_text = f"[red]-[/red] {details.get('title', 'Untitled')}"
            if details.get("column"):
                detail_text += f" (from {details['column']})"

        elif change.change_type == "card_modified":
            parts = []
            if details.get("old_title") != details.get("new_title"):
                parts.append(f"title: '{details.get('old_title')}' → '{details.get('new_title')}'")
            if details.get("old_column") != details.get("new_column"):
                parts.append(f"column: {details.get('old_column')} → {details.get('new_column')}")
            if details.get("old_description") != details.get("new_description"):
                parts.append("description changed")
            if details.get("old_link") != details.get("new_link"):
                parts.append("link changed")
            detail_text = ", ".join(parts) if parts else "modified"

        else:
            detail_text = str(details)

        table.add_row(
            change.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            change_type,
            change.card_id,
            detail_text,
        )

    console.print(table)
    console.print()
