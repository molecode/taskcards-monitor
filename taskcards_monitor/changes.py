"""Typed dataclasses for change detection.

This module defines strongly-typed dataclasses for representing changes
to TaskCards boards.
"""

from dataclasses import dataclass, field


@dataclass
class AttachmentData:
    """Represents an attachment on a card.

    Attributes:
        id: Unique attachment identifier
        filename: Name of the attached file
        download_link: URL to download the attachment
        mime_type: MIME type of the file
        length: Size of the file in bytes
    """

    id: str
    filename: str
    download_link: str
    mime_type: str | None = None
    length: int | None = None


@dataclass
class CardAdded:
    """Represents a card that was added to the board.

    Attributes:
        id: Unique card identifier
        title: Card title
        description: Card description
        link: URL link associated with the card
        column: Column/list name where the card is located
        attachments: List of attachments on the card
    """

    id: str
    title: str
    description: str
    link: str
    column: str | None
    attachments: list[AttachmentData] = field(default_factory=list)


@dataclass
class CardRemoved:
    """Represents a card that was removed from the board.

    Attributes:
        id: Unique card identifier
        title: Card title
        description: Card description
        link: URL link associated with the card
        column: Column/list name where the card was located
        attachments: List of attachments that were on the card
    """

    id: str
    title: str
    description: str
    link: str
    column: str | None
    attachments: list[AttachmentData] = field(default_factory=list)


@dataclass
class CardModified:
    """Represents a card that was modified.

    Attributes:
        id: Unique card identifier
        old_title: Previous card title
        new_title: New card title
        old_description: Previous card description
        new_description: New card description
        old_link: Previous URL link
        new_link: New URL link
        old_column: Previous column/list name
        new_column: New column/list name
        attachments_added: List of attachments that were added
        attachments_removed: List of attachments that were removed
    """

    id: str
    old_title: str
    new_title: str
    old_description: str
    new_description: str
    old_link: str
    new_link: str
    old_column: str | None
    new_column: str | None
    attachments_added: list[AttachmentData] = field(default_factory=list)
    attachments_removed: list[AttachmentData] = field(default_factory=list)


@dataclass
class ChangeSet:
    """Collection of all changes detected during monitoring.

    Attributes:
        cards_added: List of cards that were added
        cards_removed: List of cards that were removed
        cards_modified: List of cards that were modified
        is_first_run: True if this is the first check (no previous state)
        cards_count: Total number of cards in the current state
    """

    cards_added: list[CardAdded] = field(default_factory=list)
    cards_removed: list[CardRemoved] = field(default_factory=list)
    cards_modified: list[CardModified] = field(default_factory=list)
    is_first_run: bool = False
    cards_count: int = 0

    def has_changes(self) -> bool:
        """Check if there are any changes.

        Returns:
            True if there are any added, removed, or modified cards
        """
        return bool(self.cards_added or self.cards_removed or self.cards_modified)
