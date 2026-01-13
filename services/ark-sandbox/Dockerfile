FROM python:3.12.9-slim

WORKDIR /app

# Create non-root user first
RUN adduser --system --uid 1001 --home /home/arksandbox arksandbox && \
    apt-get update && \
    apt-get upgrade -y libpam0g libsqlite3-0 zlib1g libgnutls30 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /home/arksandbox && \
    chown -R arksandbox:nogroup /home/arksandbox

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy source code
COPY src/ ./src/

# Sync dependencies
RUN uv sync --frozen --no-install-project

# Set up directories for non-root user
RUN mkdir -p /home/arksandbox/.cache/uv && \
    chown -R arksandbox:nogroup /home/arksandbox && \
    chown -R arksandbox:nogroup /app

# Switch to non-root user
USER arksandbox

# Set HOME environment variable to fix uv cache location
ENV HOME=/home/arksandbox
ENV XDG_CACHE_HOME=/home/arksandbox/.cache
ENV PYTHONPATH=/app/src

# Expose port 2628 (SAND on dial pad)
EXPOSE 2628

# Run the combined controller + MCP server
CMD ["uv", "run", "python", "src/main.py"]

