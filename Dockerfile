# Use official uv Python image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:0b074d1ae15f5c3f1861354917d356e5afbd5a4c53c1190e81ad2f2add46e45b

# Set working directory
WORKDIR /app

# Create non-root user
RUN groupadd -r taskcards && \
    useradd -r -g taskcards -u 1000 -d /app -s /bin/bash taskcards && \
    mkdir -p /app/.cache/taskcards-monitor && \
    chown -R taskcards:taskcards /app

# Copy dependency files
COPY --chown=taskcards:taskcards pyproject.toml uv.lock ./

# Switch to non-root user before installing dependencies
USER taskcards

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY --chown=taskcards:taskcards taskcards_monitor/ ./taskcards_monitor/

# Set Python path
ENV PYTHONPATH=/app

# Default entrypoint
ENTRYPOINT ["uv", "run", "taskcards-monitor"]

# Default command (show help)
CMD ["--help"]
