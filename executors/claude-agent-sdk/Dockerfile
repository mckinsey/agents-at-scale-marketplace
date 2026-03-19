FROM python:3.12-slim

WORKDIR /app

# Create non-root user first
RUN adduser --system --uid 1001 --home /home/executor executor && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /home/executor/.cache/uv && \
    chown -R executor:nogroup /home/executor

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml setup.cfg README.md ./
COPY src/ ./src/

# Sync dependencies
RUN uv sync --no-install-project

# Set up directories for non-root user
RUN mkdir -p /home/executor/.cache/uv /data/sessions && \
    chown -R executor:nogroup /home/executor && \
    chown -R executor:nogroup /app && \
    chown -R executor:nogroup /data/sessions

# Switch to non-root user
USER executor

# Set HOME environment variable to fix uv cache location
ENV HOME=/home/executor
ENV XDG_CACHE_HOME=/home/executor/.cache
ENV PYTHONPATH=/app/src

# Expose the default port
EXPOSE 8000

CMD ["uv", "run", "executor-claude-agent-sdk"]
