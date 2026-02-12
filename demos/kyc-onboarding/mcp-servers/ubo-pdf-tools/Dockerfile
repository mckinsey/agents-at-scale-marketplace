# UBO PDF Tools MCP Server
# Production-grade multi-stage build with proper package installation

FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata and source for proper installation
COPY pyproject.toml uv.lock* README.md ./
COPY src ./src

# Install ubo-resolver packages as proper Python packages
# This makes ubo_infra, ubo_domain, ubo_engine importable without path hacks
RUN pip install --no-cache-dir --user .

# Copy MCP server requirements and install
COPY mcp-servers/ubo-pdf-tools/requirements.txt ./mcp-requirements.txt
RUN pip install --no-cache-dir --user -r mcp-requirements.txt


# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install Chromium for Kaleido (PNG/SVG export)
# Using Chromium instead of Chrome for better ARM64/cross-platform support
RUN apt-get update && apt-get install -y \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set Chrome path for Kaleido (using Chromium)
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMIUM_FLAGS="--no-sandbox --disable-gpu"

# Copy MCP server code
COPY mcp-servers/ubo-pdf-tools/main.py .
COPY mcp-servers/ubo-pdf-tools/scout_tools.py .

# Copy application config (loader looks for config.yaml in working dir)
COPY config/app-config.yaml ./config.yaml

# Create writable directories for ChromaDB and artifacts
RUN mkdir -p /app/artifacts /app/data && \
    chmod 777 /app/artifacts /app/data

# Expose HTTP port for MCP
EXPOSE 8080

# Environment variables (can be overridden at runtime)
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 8080)); s.close()" || exit 1

# Run the MCP server
CMD ["python", "main.py"]
