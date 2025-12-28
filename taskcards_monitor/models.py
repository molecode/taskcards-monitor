"""Peewee ORM models for TaskCards monitor database."""

from datetime import datetime

from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

# Database instance (will be initialized in database.py)
db = SqliteDatabase(None)


class BaseModel(Model):
    """Base model with database connection."""

    class Meta:
        database = db


class Board(BaseModel):
    """Board being monitored."""

    board_id = CharField(primary_key=True)
    name = CharField(null=True)
    description = TextField(null=True)
    first_checked = DateTimeField(default=datetime.now)
    last_checked = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "boards"


class Card(BaseModel):
    """
    Card with temporal tracking (history built-in).

    Uses valid_from/valid_to pattern:
    - Current state: valid_to IS NULL
    - Historical states: valid_to is set to when it was superseded
    """

    board = ForeignKeyField(Board, backref="cards", on_delete="CASCADE")
    card_id = CharField()
    title = CharField(null=True)
    description = TextField(null=True)
    link = CharField(null=True)
    list_id = CharField(null=True)
    list_name = CharField(null=True)
    valid_from = DateTimeField(default=datetime.now, index=True)
    valid_to = DateTimeField(null=True, index=True)

    class Meta:
        table_name = "cards"
        indexes = (
            # Unique constraint on board + card_id + valid_from
            (("board", "card_id", "valid_from"), True),
            # Index for querying current state
            (("board", "card_id", "valid_to"), False),
        )


class List(BaseModel):
    """
    List/column with temporal tracking.

    Tracks column renames and position changes over time.
    """

    board = ForeignKeyField(Board, backref="lists", on_delete="CASCADE")
    list_id = CharField()
    name = CharField()
    position = IntegerField(null=True)
    color = CharField(null=True)
    valid_from = DateTimeField(default=datetime.now, index=True)
    valid_to = DateTimeField(null=True, index=True)

    class Meta:
        table_name = "lists"
        indexes = (
            (("board", "list_id", "valid_from"), True),
            (("board", "list_id", "valid_to"), False),
        )


class Change(BaseModel):
    """
    Change event log.

    Stores detailed information about each change for querying
    "what changed when" without reconstructing from temporal tables.
    """

    board = ForeignKeyField(Board, backref="changes", on_delete="CASCADE")
    timestamp = DateTimeField(default=datetime.now, index=True)
    change_type = CharField()  # 'card_added', 'card_removed', 'card_modified', 'card_moved'
    card_id = CharField()
    details = TextField()  # JSON string with full change details

    class Meta:
        table_name = "changes"
        indexes = (
            (("board", "timestamp"), False),
            (("board", "card_id", "timestamp"), False),
        )


class Attachment(BaseModel):
    """
    Attachment with temporal tracking.

    Tracks when attachments are added/removed from cards.
    """

    board = ForeignKeyField(Board, backref="attachments", on_delete="CASCADE")
    card_id = CharField()
    attachment_id = CharField()
    filename = CharField(null=True)
    url = CharField(null=True)
    mime_type = CharField(null=True)
    length = IntegerField(null=True)
    added_at = DateTimeField(default=datetime.now, index=True)
    removed_at = DateTimeField(null=True, index=True)

    class Meta:
        table_name = "attachments"
        indexes = (
            (("board", "card_id", "attachment_id", "added_at"), True),
            (("board", "card_id", "removed_at"), False),
        )
