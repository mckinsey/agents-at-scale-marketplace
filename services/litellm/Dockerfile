FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Create non-root user
RUN adduser --system --uid 1001 --home /home/provider provider && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /home/provider/.cache/uv && \
    chown -R provider:nogroup /home/provider

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml setup.cfg README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-install-project

RUN chown -R provider:nogroup /app

USER provider

ENV HOME=/home/provider
ENV XDG_CACHE_HOME=/home/provider/.cache
ENV PYTHONPATH=/app/src

CMD ["uv", "run", "litellm-model-provider"]
