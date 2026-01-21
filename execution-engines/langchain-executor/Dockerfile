FROM python:3.12.9-slim

WORKDIR /app

# Create non-root user
RUN adduser --system --uid 1001 --home /home/executor executor && \
    apt-get update && \
    apt-get upgrade -y libpam0g libsqlite3-0 zlib1g libgnutls30 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /home/executor/.cache/uv && \
    chown -R executor:nogroup /home/executor

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Sync dependencies (uses published ark-sdk from PyPI)
RUN uv sync --frozen --no-install-project || uv sync --no-install-project

# Set up directories for non-root user
RUN chown -R executor:nogroup /app

USER executor

ENV HOME=/home/executor
ENV XDG_CACHE_HOME=/home/executor/.cache

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "langchain_executor"]
