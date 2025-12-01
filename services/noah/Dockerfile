FROM python:3.11-slim

# Install all system dependencies in one layer
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    git \
    ca-certificates \
    gnupg \
    postgresql-client \
    wget \
    erlang-base \
    rabbitmq-server \
    && rm -rf /var/lib/apt/lists/* \
    && systemctl disable rabbitmq-server 2>/dev/null || true

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create working directory
WORKDIR /app

# Copy dependency files first (most likely to change)
COPY pyproject.toml README.md uv.lock* ./
COPY requirements.txt ./

# Install Python dependencies
RUN uv sync --no-dev

# Install additional Python packages for system operations
RUN pip install -r requirements.txt

# Copy source code last (changes most frequently)
COPY src/ ./src/

# Set default port
ENV PORT=8639

# Expose port
EXPOSE ${PORT}

# Run the MCP server with FastMCP CLI
CMD ["sh", "-c", "uv run fastmcp run src/ark_runtime_mcp/server.py --transport http --port $PORT --host 0.0.0.0"]