FROM python:3.11-slim

# Install system dependencies for whisper (ffmpeg is required)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Create data, cache, and home directories
RUN mkdir -p /data/whisper-cache /home/mcp && \
    useradd -r -s /bin/false -d /home/mcp mcp && \
    chown -R mcp:mcp /app /data /home/mcp

USER mcp

EXPOSE 8080

CMD ["python", "src/server.py"]
