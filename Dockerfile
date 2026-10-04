# Use official uv Alpine image with Python (pinned to specific version)
FROM ghcr.io/astral-sh/uv:0.12.23-python3.12-alpine@sha256:8dc70d017b5b726727fb4801ef52103556d39d80ada96a13b77b52f073b693dc

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup -S taskcards && \
    adduser -S -G taskcards -u 1000 -h /app taskcards && \
    mkdir -p /app/.cache/taskcards-monitor && \
    chown -R taskcards:taskcards /app

# Copy application files
COPY --chown=taskcards:taskcards pyproject.toml uv.lock README.md ./
COPY --chown=taskcards:taskcards taskcards_monitor/ ./taskcards_monitor/

# Switch to non-root user before installing
USER taskcards

# Install dependencies and the package (not editable, baked into image)
RUN uv sync --frozen --no-dev --no-editable

# Add virtual environment to PATH so we can run commands directly
ENV PATH="/app/.venv/bin:$PATH"

# Default entrypoint - run directly from venv (no uv run needed)
ENTRYPOINT ["taskcards-monitor"]

# Default command (show help)
CMD ["--help"]
