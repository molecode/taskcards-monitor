# taskcards-monitor

Monitor [TaskCards](https://www.taskcards.de) boards for card changes using browser automation.

## Features

- Monitor both **public and private** TaskCards boards
- Detect added/removed cards
- Detect card title changes
- Uses Playwright browser automation
- Persistent state tracking

## Installation

```bash
# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
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
- `--headless/--no-headless` - Run browser in headless mode (default: headless)
- `-v, --verbose` - Enable verbose logging

### Examples

```bash
# Check a private board for changes (saves state)
uv run taskcards-monitor check BOARD_ID --token VIEW_TOKEN

# Check with visible browser (useful for seeing what's happening)
uv run taskcards-monitor check BOARD_ID --token VIEW_TOKEN --no-headless

# Show saved state
uv run taskcards-monitor show BOARD_ID

# List all monitored boards
uv run taskcards-monitor list

# Inspect board with detailed output (debugging, doesn't save state)
uv run taskcards-monitor inspect BOARD_ID --token VIEW_TOKEN

# Inspect and save screenshot
uv run taskcards-monitor inspect BOARD_ID --token VIEW_TOKEN --screenshot board.png

# Verbose mode (shows detailed progress)
uv run taskcards-monitor check BOARD_ID --token VIEW_TOKEN -v
```

## State Files

State files are saved in `~/.cache/taskcards-monitor/BOARD_ID.json`

### Technical Details

- Uses **Playwright** for browser automation (headless Chromium)
- Scrapes data from the rendered DOM (TaskCards uses Vue.js but doesn't expose the store)

### Why Playwright?

TaskCards is a client-side rendered application that requires JavaScript to load. The data is not available via a simple HTTP API. Using browser automation allows us to:
- Access boards that require authentication (view tokens)
- Extract data from the fully rendered page
- Monitor boards exactly as a user would see them

## Output Example

When changes are detected:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Cards Added                ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
┃ Title                                 ┃
├───────────────────────────────────────┤
│ New homework assignment               │
└───────────────────────────────────────┘

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            Cards Changed                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
┃ Old Title       │ New Title                   ┃
├─────────────────┼─────────────────────────────┤
│ Old assignment  │ Updated assignment details  │
└─────────────────┴─────────────────────────────┘
```

## Troubleshooting

### Browser Installation Issues

If you get errors about missing browsers:

```bash
# Reinstall Playwright browsers
uv run playwright install chromium

# Or with system dependencies (Linux)
uv run playwright install --with-deps chromium
```

### Board Access Issues

- **Private boards**: Make sure you're using the correct view token
- **Token format**: Tokens are UUIDs (found in the board URL)

### Debugging

Use the `--no-headless` flag to see what the browser is doing:

```bash
uv run taskcards-monitor check BOARD_ID --token TOKEN --no-headless
```

Use the `inspect` command to take screenshots:

```bash
uv run taskcards-monitor inspect BOARD_ID --token TOKEN --screenshot debug.png
```

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
├── fetcher.py        # Playwright-based browser automation for fetching board data
└── monitor.py        # Change detection logic and state management
```

## Future Enhancements

Planned features (not yet implemented):
- Email notifications
- Change history tracking
- Track card descriptions and other metadata

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
