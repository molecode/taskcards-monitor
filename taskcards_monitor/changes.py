"""Typed dataclasses for change detection.

This module defines strongly-typed dataclasses for representing changes
to TaskCards boards, replacing the previous dictionary-based approach
for better type safety and IDE support.
"""

from dataclasses import dataclass, field
from typing import Any


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttachmentData":
        """Create AttachmentData from dictionary.

        Args:
            data: Dictionary with attachment data

        Returns:
            AttachmentData instance
        """
        return cls(
            id=data.get("id", ""),
            filename=data.get("filename", ""),
            download_link=data.get("downloadLink", ""),
            mime_type=data.get("mimetype"),
            length=data.get("length"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "filename": self.filename,
            "downloadLink": self.download_link,
            "mimetype": self.mime_type,
            "length": self.length,
        }


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CardAdded":
        """Create CardAdded from dictionary.

        Args:
            data: Dictionary with card data

        Returns:
            CardAdded instance
        """
        attachments = [AttachmentData.from_dict(att) for att in data.get("attachments", [])]
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            link=data.get("link", ""),
            column=data.get("column"),
            attachments=attachments,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "column": self.column,
            "attachments": [att.to_dict() for att in self.attachments],
        }


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CardRemoved":
        """Create CardRemoved from dictionary.

        Args:
            data: Dictionary with card data

        Returns:
            CardRemoved instance
        """
        attachments = [AttachmentData.from_dict(att) for att in data.get("attachments", [])]
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            link=data.get("link", ""),
            column=data.get("column"),
            attachments=attachments,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "column": self.column,
            "attachments": [att.to_dict() for att in self.attachments],
        }


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CardModified":
        """Create CardModified from dictionary.

        Args:
            data: Dictionary with card change data

        Returns:
            CardModified instance
        """
        attachments_added = [
            AttachmentData.from_dict(att) for att in data.get("attachments_added", [])
        ]
        attachments_removed = [
            AttachmentData.from_dict(att) for att in data.get("attachments_removed", [])
        ]
        return cls(
            id=data.get("id", ""),
            old_title=data.get("old_title", ""),
            new_title=data.get("new_title", ""),
            old_description=data.get("old_description", ""),
            new_description=data.get("new_description", ""),
            old_link=data.get("old_link", ""),
            new_link=data.get("new_link", ""),
            old_column=data.get("old_column"),
            new_column=data.get("new_column"),
            attachments_added=attachments_added,
            attachments_removed=attachments_removed,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "old_title": self.old_title,
            "new_title": self.new_title,
            "old_description": self.old_description,
            "new_description": self.new_description,
            "old_link": self.old_link,
            "new_link": self.new_link,
            "old_column": self.old_column,
            "new_column": self.new_column,
            "attachments_added": [att.to_dict() for att in self.attachments_added],
            "attachments_removed": [att.to_dict() for att in self.attachments_removed],
        }


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChangeSet":
        """Create ChangeSet from dictionary.

        Args:
            data: Dictionary with change data

        Returns:
            ChangeSet instance
        """
        cards_added = [CardAdded.from_dict(c) for c in data.get("cards_added", [])]
        cards_removed = [CardRemoved.from_dict(c) for c in data.get("cards_removed", [])]
        cards_modified = [CardModified.from_dict(c) for c in data.get("cards_changed", [])]

        return cls(
            cards_added=cards_added,
            cards_removed=cards_removed,
            cards_modified=cards_modified,
            is_first_run=data.get("is_first_run", False),
            cards_count=data.get("cards_count", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for backward compatibility.

        Note: Uses 'cards_changed' key for modified cards to maintain
        backward compatibility with existing code.

        Returns:
            Dictionary representation
        """
        return {
            "cards_added": [c.to_dict() for c in self.cards_added],
            "cards_removed": [c.to_dict() for c in self.cards_removed],
            "cards_changed": [c.to_dict() for c in self.cards_modified],
            "is_first_run": self.is_first_run,
            "cards_count": self.cards_count,
        }

    def has_changes(self) -> bool:
        """Check if there are any changes.

        Returns:
            True if there are any added, removed, or modified cards
        """
        return bool(self.cards_added or self.cards_removed or self.cards_modified)
