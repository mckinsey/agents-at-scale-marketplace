FROM python:3.11-slim

# Declare build arguments for multi-arch support
ARG TARGETARCH

# Install all system dependencies in one layer
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    git \
    ca-certificates \
    gnupg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl (architecture-aware)
RUN KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt) && \
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install helm (auto-detects architecture)
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install argo CLI (architecture-aware)
RUN ARGO_ARCH=$([ "${TARGETARCH}" = "arm64" ] && echo "arm64" || echo "amd64") && \
    curl -sLO "https://github.com/argoproj/argo-workflows/releases/latest/download/argo-linux-${ARGO_ARCH}.gz" \
    && gunzip "argo-linux-${ARGO_ARCH}.gz" \
    && chmod +x "argo-linux-${ARGO_ARCH}" \
    && mv "argo-linux-${ARGO_ARCH}" /usr/local/bin/argo

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