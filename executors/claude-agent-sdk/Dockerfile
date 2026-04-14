# Stage 1: Build the claude-agent-sdk wheel for Linux
FROM python:3.12-slim AS sdk-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install build twine

WORKDIR /build
RUN git clone --depth 1 https://github.com/anthropics/claude-agent-sdk-python.git .

# Install the Claude Code CLI via npm so build_wheel.py can find it,
# then build the wheel with --skip-download (use the npm-installed binary)
RUN npm install -g @anthropic-ai/claude-code && \
    mkdir -p src/claude_agent_sdk/_bundled && \
    cp $(which claude) src/claude_agent_sdk/_bundled/claude && \
    chmod +x src/claude_agent_sdk/_bundled/claude && \
    python scripts/build_wheel.py --skip-download --clean

# Stage 2: Application image
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Create non-root user and install Node.js (required at runtime by Claude Agent SDK CLI)
RUN adduser --system --uid 1001 --home /home/executor executor && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /home/executor/.cache/uv && \
    chown -R executor:nogroup /home/executor

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the pre-built Linux wheel from builder
COPY --from=sdk-builder /build/dist/*.whl /tmp/sdk/

# Copy project files
COPY pyproject.toml setup.cfg README.md uv.lock ./
COPY src/ ./src/

# Sync dependencies first (creates .venv), then install the pre-built SDK wheel into it
RUN uv sync --no-install-project && \
    uv pip install /tmp/sdk/*.whl && \
    rm -rf /tmp/sdk

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
