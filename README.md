# taskcards-monitor

 Monitor [TaskCards](https://www.taskcards.de) boards for card changes via the GraphQL API.

## Features

- Monitor both **public and private** TaskCards boards
- Detect added/removed cards
- Detect card title and description changes
- Persistent state tracking with full board data

## Installation

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
```

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
- Email notifications
- Change history tracking

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
