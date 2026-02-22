# Use official uv Alpine image with Python (pinned to specific version)
FROM ghcr.io/astral-sh/uv:0.10.4-python3.12-alpine@sha256:a5e952bef986128f6b4823165cec69db4e2eae69b22848f576ad4b22fdf8b069

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
