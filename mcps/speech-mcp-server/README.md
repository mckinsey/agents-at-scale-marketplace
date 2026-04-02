# Speech MCP Server

Local audio transcription via OpenAI Whisper, exposed as an MCP tool over StreamableHTTP.

## Features

- **transcribe_audio**: Transcribe audio files (mp3, mp4, m4a, wav, ogg, flac, webm) using Whisper
- Caches transcription results by file hash
- Configurable Whisper model size

## Quick Start

```bash
# Build Docker image
docker build -t speech-mcp-server:latest .

# Deploy with Helm
helm install speech-mcp-server ./chart -n default --create-namespace

# Verify
kubectl get mcpserver speech-mcp-server
kubectl get pods -l app=speech-mcp-server
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8080` |
| `BASE_DATA_DIR` | Base directory for audio files | `/data` |
| `WHISPER_MODEL` | Whisper model size (tiny, base, small, medium, large) | `small` |
| `CACHE_DIR` | Transcription cache directory | `/data/whisper-cache` |

## Dependencies

- openai-whisper
- starlette
- uvicorn
