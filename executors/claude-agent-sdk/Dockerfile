# Stage 1: Build the claude-agent-sdk wheel for Linux
FROM python:3.12-slim AS sdk-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install build twine

WORKDIR /build
RUN git clone --depth 1 https://github.com/anthropics/claude-agent-sdk-python.git . && \
    python scripts/build_wheel.py --clean

# Stage 2: Application image
FROM python:3.12-slim

WORKDIR /app

# Create non-root user first
RUN adduser --system --uid 1001 --home /home/executor executor && \
    apt-get update && \
    apt-get upgrade -y && \
    # Node.js is required at runtime by the Claude Agent SDK CLI
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /home/executor/.cache/uv && \
    chown -R executor:nogroup /home/executor

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the pre-built Linux wheel from builder
COPY --from=sdk-builder /build/dist/*.whl /tmp/sdk/

# Copy project files
COPY pyproject.toml setup.cfg README.md ./
COPY src/ ./src/

# Install the pre-built SDK wheel first, then sync remaining dependencies
RUN uv pip install --system /tmp/sdk/*.whl && \
    rm -rf /tmp/sdk && \
    uv sync --no-install-project

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
