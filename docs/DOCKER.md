# Docker Usage Guide

This guide explains how to use the taskcards-monitor Docker container for automated monitoring with cron.

## Quick Start

### Pull the Image

```bash
docker pull ghcr.io/molecode/taskcards-monitor:latest
```

### Run a One-Time Check

```bash
docker run --rm \
  -v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor \
  ghcr.io/molecode/taskcards-monitor:latest \
  check BOARD_ID --token VIEW_TOKEN
```

## Setup for Cron Jobs

### 1. Create a Configuration Directory

```bash
mkdir -p ~/taskcards-monitor/{config,cache}
```

### 2. Create Email Configuration (Optional)

Create `~/taskcards-monitor/config/email-config.yaml`:

```yaml
smtp:
  host: smtp.gmail.com
  port: 587
  use_tls: true
  username: your-email@gmail.com
  password: your-app-password

email:
  from: your-email@gmail.com
  from_name: TaskCards Monitor
  to:
    - recipient@example.com
  subject: "📋 Changes on {{ board_name }}"
```

### 3. Create a Monitoring Script

Create `~/taskcards-monitor/monitor.sh`:

```bash
#!/bin/bash

# Configuration
BOARD_ID="your-board-id"
VIEW_TOKEN="your-view-token"
IMAGE="ghcr.io/molecode/taskcards-monitor:latest"

# Paths
CACHE_DIR="${HOME}/taskcards-monitor/cache"
CONFIG_DIR="${HOME}/taskcards-monitor/config"

# Pull latest image (optional, comment out for faster runs)
docker pull "${IMAGE}" > /dev/null 2>&1

# Run the monitor
docker run --rm \
  -v "${CACHE_DIR}:/app/.cache/taskcards-monitor" \
  -v "${CONFIG_DIR}:/config:ro" \
  "${IMAGE}" \
  check "${BOARD_ID}" \
  --token "${VIEW_TOKEN}" \
  --email-config /config/email-config.yaml

# Exit with the same status as the container
exit $?
```

Make it executable:

```bash
chmod +x ~/taskcards-monitor/monitor.sh
```

### 4. Configure Crontab

Edit your crontab:

```bash
crontab -e
```

Add an entry to run every 3 hours:

```cron
# Run taskcards-monitor every 3 hours
0 */3 * * * /home/yourusername/taskcards-monitor/monitor.sh >> /home/yourusername/taskcards-monitor/cron.log 2>&1
```

Or use a more specific schedule:

```cron
# Run at 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, and 9 PM every day
0 6,9,12,15,18,21 * * * /home/yourusername/taskcards-monitor/monitor.sh >> /home/yourusername/taskcards-monitor/cron.log 2>&1
```

## Docker Compose (Alternative)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  taskcards-monitor:
    image: ghcr.io/molecode/taskcards-monitor:latest
    volumes:
      - ./cache:/app/.cache/taskcards-monitor
      - ./config:/config:ro
    command: check ${BOARD_ID} --token ${VIEW_TOKEN} --email-config /config/email-config.yaml
    environment:
      - BOARD_ID=${BOARD_ID}
      - VIEW_TOKEN=${VIEW_TOKEN}
```

Create `.env` file:

```env
BOARD_ID=your-board-id
VIEW_TOKEN=your-view-token
```

Then run with cron:

```bash
#!/bin/bash
cd ~/taskcards-monitor
docker compose pull > /dev/null 2>&1
docker compose run --rm taskcards-monitor
```

## Monitoring Multiple Boards

Create a script that monitors multiple boards:

```bash
#!/bin/bash

IMAGE="ghcr.io/molecode/taskcards-monitor:latest"
CACHE_DIR="${HOME}/taskcards-monitor/cache"
CONFIG_DIR="${HOME}/taskcards-monitor/config"

# Board configurations (ID:TOKEN pairs)
declare -a BOARDS=(
  "board-id-1:view-token-1"
  "board-id-2:view-token-2"
  "board-id-3:view-token-3"
)

# Monitor each board
for board in "${BOARDS[@]}"; do
  IFS=':' read -r BOARD_ID TOKEN <<< "$board"

  echo "Checking board: ${BOARD_ID}"

  docker run --rm \
    -v "${CACHE_DIR}:/app/.cache/taskcards-monitor" \
    -v "${CONFIG_DIR}:/config:ro" \
    "${IMAGE}" \
    check "${BOARD_ID}" \
    --token "${TOKEN}" \
    --email-config /config/email-config.yaml

  echo "---"
done
```

## Available Commands

The Docker container supports all taskcards-monitor commands:

```bash
# Check for changes
docker run --rm -v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor \
  ghcr.io/molecode/taskcards-monitor:latest \
  check BOARD_ID --token TOKEN

# Show saved state
docker run --rm -v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor \
  ghcr.io/molecode/taskcards-monitor:latest \
  show BOARD_ID

# List all monitored boards
docker run --rm -v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor \
  ghcr.io/molecode/taskcards-monitor:latest \
  list

# Inspect board (debugging)
docker run --rm \
  ghcr.io/molecode/taskcards-monitor:latest \
  inspect BOARD_ID --token TOKEN
```

## Volume Mounts Explained

- **Cache Volume** (`-v ~/.cache/taskcards-monitor:/app/.cache/taskcards-monitor`):
  - Stores board state between runs
  - Required for change detection to work
  - Should be persistent

- **Config Volume** (`-v ~/config:/config:ro`):
  - Provides email configuration
  - Read-only (`:ro`) for security
  - Optional if not using email notifications

## Image Tags

Docker images are built automatically when a new release is published on GitHub.

- `latest` - Latest stable release
- `0.2.0` - Specific version tag (matches release version)
- `0.2` - Major.minor version tag
- `0` - Major version tag

**Example**: When you publish release `v0.2.0` (or `0.2.0`), the following tags are created:
- `ghcr.io/molecode/taskcards-monitor:latest`
- `ghcr.io/molecode/taskcards-monitor:0.2.0`
- `ghcr.io/molecode/taskcards-monitor:0.2`
- `ghcr.io/molecode/taskcards-monitor:0`

## Building Locally

```bash
# Build the image
docker build -t taskcards-monitor .

# Run it
docker run --rm taskcards-monitor --help
```

## Troubleshooting

### Permission Issues

If you encounter permission errors with the cache directory:

```bash
# Fix permissions
sudo chown -R $(id -u):$(id -g) ~/taskcards-monitor/cache
```

### Container Doesn't Start

Check the logs:

```bash
docker logs taskcards-monitor
```

### Cron Job Not Running

1. Check cron is running: `systemctl status cron`
2. Check cron logs: `grep CRON /var/log/syslog`
3. Verify script has execute permissions: `ls -la ~/taskcards-monitor/monitor.sh`
4. Check the cron log file: `tail -f ~/taskcards-monitor/cron.log`

### State Not Persisting

Ensure the cache volume is mounted correctly and the directory exists:

```bash
ls -la ~/taskcards-monitor/cache
```

## Security Notes

- The container runs as a non-root user (UID 1000)
- Mount config volumes as read-only when possible (`:ro`)
- Store sensitive tokens in environment variables or secure configuration files
- Never commit tokens or passwords to version control
