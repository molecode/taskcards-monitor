# taskcards-monitor

 Monitor [TaskCards](https://www.taskcards.de) boards for card changes via the GraphQL API.

## Features

- Monitor both **public and private** TaskCards boards
- Detect added/removed cards
- Detect card title, description, and link changes
- Track card movements between columns
- Persistent state tracking with full board data
- **Email notifications** when changes are detected (optional)

## Installation

### Using Docker (Recommended for Production)

```bash
# Pull the image
docker pull ghcr.io/molecode/taskcards-monitor:latest

# Run a check
docker run --rm \
  -v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor \
  ghcr.io/molecode/taskcards-monitor:latest \
  check BOARD_ID --token VIEW_TOKEN
```

See [Docker Usage Guide](docs/DOCKER.md) for detailed setup with cron jobs.

### Local Development

```bash
# Install dependencies
uv sync

```

## Quick Start

### Monitor a Public Board

```bash
uv run taskcards-monitor check BOARD_ID
```

### Monitor a Private Board

```bash
uv run taskcards-monitor check BOARD_ID --token VIEW_TOKEN
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
- `inspect BOARD_ID` - Explore a board with detailed output (debugging, does NOT save state)

### Options

- `--token TOKEN` or `-t TOKEN` - View token for private/protected boards
- `-v, --verbose` - Enable verbose logging
- `--email-config PATH` or `-e PATH` - Path to email configuration YAML file (enables email notifications)

### Examples

```bash
# Check a private board for changes (saves state)
uv run taskcards-monitor check BOARD_ID --token VIEW_TOKEN

# Show saved state
uv run taskcards-monitor show BOARD_ID

# List all monitored boards
uv run taskcards-monitor list

# Inspect board with detailed output (debugging, doesn't save state)
uv run taskcards-monitor inspect BOARD_ID --token VIEW_TOKEN

# Verbose mode (shows detailed progress)
uv run taskcards-monitor check BOARD_ID --token VIEW_TOKEN -v

# With email notifications
uv run taskcards-monitor check BOARD_ID --email-config email-config.yaml
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
uv run taskcards-monitor check BOARD_ID --email-config email-config.yaml
```

### Email Features

- Customizable subject line with Jinja2 template variables
- Shows added, removed, and changed cards with full details
- Displays card links as clickable hyperlinks
- Shows column information for each card
- Only sends emails when changes are detected (not on first run)
```

## What Changes Are Tracked?

taskcards-monitor detects the following changes:

- **Cards Added**: New cards appear on the board
- **Cards Removed**: Existing cards are deleted
- **Card Changes**:
  - Title changes
  - Description changes
  - Link changes (URL added, removed, or modified)
  - Column movements (cards moved between lists)

All changes are displayed in the terminal and included in email notifications if configured.

## State Files

State files are saved in `~/.cache/taskcards-monitor/BOARD_ID.json`

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

# Run pre-commit checks manually
uv run pre-commit run --all-files
```

## Project Structure

```
taskcards_monitor/
├── __init__.py       # Package initialization
├── cli.py            # Click-based CLI interface with Rich output
├── fetcher.py        # HTTP client for fetching board data via GraphQL API
└── monitor.py        # Change detection logic and state management
```

## Future Enhancements

Planned features (not yet implemented):
- Change history tracking

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
