"""Database connection and initialization."""

from pathlib import Path

from .models import Attachment, Board, Card, Change, List, db


def init_database(db_path: Path | None = None) -> None:
    """
    Initialize the database connection and create tables if needed.

    Args:
        db_path: Path to SQLite database file. If None, uses default location.
    """
    if db_path is None:
        db_path = get_default_db_path()

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database
    db.init(str(db_path))

    # Create tables if they don't exist
    db.create_tables([Board, Card, List, Change, Attachment], safe=True)


def get_default_db_path() -> Path:
    """
    Get the default database path.

    Returns:
        Path to the database file in user's cache directory
    """
    return Path.home() / ".cache" / "taskcards-monitor" / "taskcards-monitor.db"


def get_database():
    """
    Get the database instance.

    Returns:
        Database instance
    """
    return db
