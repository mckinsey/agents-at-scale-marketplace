# UBO Web Tools MCP Server Dockerfile
# Multi-stage build for smaller image size

FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir uv

# Copy dependency files (README.md required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install the ubo-resolver package
RUN uv pip install --system . --no-cache

# Copy MCP server requirements
COPY mcp-servers/ubo-web-tools/requirements.txt ./mcp-requirements.txt
RUN uv pip install --system -r mcp-requirements.txt --no-cache


# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code (for any dynamic imports)
COPY src/ /app/src/

# Set Python path to find the ubo_* modules
ENV PYTHONPATH=/app/src

# Copy MCP server
COPY mcp-servers/ubo-web-tools/main.py .

# Create directories for artifacts
RUN mkdir -p /app/artifacts && chmod 777 /app/artifacts

# Expose port (different from PDF tools)
EXPOSE 8081

# Environment variables for FastMCP
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8081

# Run the server
CMD ["python", "main.py"]
