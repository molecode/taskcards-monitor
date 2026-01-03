# taskcards-monitor

Monitor [TaskCards](https://www.taskcards.de) boards for card changes via the GraphQL API.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Using pipx (Recommended)](#using-pipx-recommended)
  - [Using Docker](#using-docker)
  - [From Source (Development)](#from-source-development)
- [Quick Start](#quick-start)
  - [Monitor a Public Board](#monitor-a-public-board)
  - [Monitor a Private Board](#monitor-a-private-board)
- [Usage](#usage)
  - [Commands](#commands)
  - [Options](#options)
  - [Examples](#examples)
- [Email Notifications](#email-notifications)
  - [Setup](#setup)
  - [Email Features](#email-features)
- [What Changes Are Tracked?](#what-changes-are-tracked)
- [Database Storage](#database-storage)
- [Development](#development)
- [Project Structure](#project-structure)
- [AI-Generated Code](#ai-generated-code)
- [Contributing](#contributing)

## Features

- Monitor both **public and private** TaskCards boards
- Detect added/removed cards
- Detect card title, description, and link changes
- Track card movements between columns
- **Track file attachments** (added/removed)
- **Complete change history** with SQLite database
- Query historical changes by date, card, or time range
- Persistent state tracking with full board data
- **Email notifications** when changes are detected (optional)

## Installation

### Using pipx (Recommended)

```bash
# Install from PyPI using pipx (recommended for CLI tools)
pipx install taskcards-monitor

# Or using pip
pip install taskcards-monitor
```

### Using Docker

**Option 1: Docker Compose**

```bash
# 1. Create required directories and .env file
mkdir -p cache config
cp .env.example .env

# 2. Edit .env with your board details
# BOARD_ID=your-board-id
# VIEW_TOKEN=your-view-token

# 3. Run the monitor
docker compose run --rm taskcards-monitor
```

**Option 2: Docker Run**

```bash
# Pull the image
docker pull ghcr.io/molecode/taskcards-monitor:latest

# Run a check
docker run --rm \
  -v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor \
  ghcr.io/molecode/taskcards-monitor:latest \
  check BOARD_ID --token VIEW_TOKEN
```

See [Docker Usage Guide](docs/DOCKER.md) for detailed setup including cron jobs and email notifications.

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/molecode/taskcards-monitor.git
cd taskcards-monitor

# Install dependencies
uv sync
```

## Quick Start

### Monitor a Public Board

```bash
taskcards-monitor check BOARD_ID
```

### Monitor a Private Board

```bash
taskcards-monitor check BOARD_ID --token VIEW_TOKEN
```

**Finding Board IDs and Tokens:**
- Board ID and token are in the URL when viewing a board:
  - Private: `https://www.taskcards.de/#/board/BOARD_ID/view?token=VIEW_TOKEN`
  - Public: `https://www.taskcards.de/#/board/BOARD_ID/view`

## Usage

### Commands

- `check BOARD_ID` - Check a board for changes and save state
- `show BOARD_ID` - Show the current saved state
- `list` - List all boards that have been checked
- `history BOARD_ID` - Show change history for a board
- `inspect BOARD_ID` - Explore a board with detailed output (debugging, does NOT save state)

### Options

- `--token TOKEN` or `-t TOKEN` - View token for private/protected boards
- `-v, --verbose` - Enable verbose logging
- `--email-config PATH` or `-e PATH` - Path to email configuration YAML file (enables email notifications)

### Examples

```bash
# Check a private board for changes (saves state)
taskcards-monitor check BOARD_ID --token VIEW_TOKEN

# Show saved state
taskcards-monitor show BOARD_ID

# List all monitored boards
taskcards-monitor list

# View change history for a board
taskcards-monitor history BOARD_ID

# View history with filters
taskcards-monitor history BOARD_ID --since 2025-12-01
taskcards-monitor history BOARD_ID --limit 50
taskcards-monitor history BOARD_ID --card CARD_ID

# Inspect board with detailed output (debugging, doesn't save state)
taskcards-monitor inspect BOARD_ID --token VIEW_TOKEN

# Verbose mode (shows detailed progress)
taskcards-monitor check BOARD_ID --token VIEW_TOKEN -v

# With email notifications
taskcards-monitor check BOARD_ID --email-config email-config.yaml
```

## Email Notifications

Get notified via email when changes are detected on your boards.

### Setup

1. Copy the example configuration file:
```bash
cp email-config.example.yaml email-config.yaml
```

2. Edit `email-config.yaml` with your SMTP settings and recipient emails:
```yaml
smtp:
  host: <smtp-server>
  port: 587
  use_tls: true
  username: <your-username>
  password: <your-password>

email:
  from: your-email@gmail.com
  from_name: TaskCards Monitor
  to:
    - recipient1@example.com
    - recipient2@example.com
  # Subject supports Jinja2 variables: board_name, board_id, added_count, removed_count, changed_count
  subject: "📋 Changes on {{ board_name }} - {{ added_count }} added, {{ removed_count }} removed"
```

3. Run the check command with the email config:
```bash
taskcards-monitor check BOARD_ID --email-config email-config.yaml
```

### Email Features

- Customizable subject line with Jinja2 template variables
- Shows added, removed, and changed cards with full details
- Displays card links as clickable hyperlinks
- Shows file attachments with download links and sizes
- Shows column information for each card
- Only sends emails when changes are detected (not on first run)

## What Changes Are Tracked?

taskcards-monitor detects the following changes:

- **Cards Added**: New cards appear on the board
- **Cards Removed**: Existing cards are deleted
- **Card Changes**:
  - Title changes
  - Description changes
  - Link changes (URL added, removed, or modified)
  - Column movements (cards moved between lists)
  - Attachments added or removed (with filenames and file sizes)

All changes are displayed in the terminal and included in email notifications if configured.

## Database Storage

Board state and change history are stored in a SQLite database at:
```
~/.cache/taskcards-monitor/taskcards-monitor.db
```

This database contains:
- **Current state** of all monitored boards
- **Complete change history** with timestamps
- **Temporal tracking** of cards, lists, and attachments

The database provides:
- Fast queries for historical data
- Efficient storage with indexing
- Point-in-time state reconstruction
- Detailed audit trail of all changes

## Development

```bash
# Install dependencies (including dev tools)
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install

# Run linter
uv run ruff check taskcards_monitor/

# Auto-fix linting issues
uv run ruff check --fix taskcards_monitor/

# Format code
uv run ruff format taskcards_monitor/

# Run type checker
uv run ty check

# Run pre-commit checks manually
uv run pre-commit run --all-files
```

## Project Structure

```
taskcards_monitor/
├── __init__.py          # Package initialization
├── changes.py           # Typed dataclasses for change detection
├── cli.py               # Click-based CLI interface
├── database.py          # Database connection and initialization
├── display.py           # Rich output formatting and tables
├── email_notifier.py    # Email notification functionality
├── email_template.html  # HTML template for email notifications
├── fetcher.py           # HTTP client for fetching board data via GraphQL API
├── models.py            # Peewee ORM models (Board, Card, List, Change, Attachment)
└── monitor.py           # Change detection logic and state management
```

## AI-Generated Code

This project was developed mainly with the assistance of [Claude Code](https://claude.ai/code).

While AI assisted in generating the code, all output has been reviewed and tested to ensure:
- **Security**: Proper handling of credentials and tokens
- **Functionality**: Reliable change detection across different board configurations
- **Best Practices**: Adherence to Python development standards
- **Documentation**: Comprehensive usage examples and setup instructions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
