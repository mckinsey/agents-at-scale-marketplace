# File API

FastAPI service for S3 file operations via VersityGW.

## Quickstart

```bash
make help

make init
make dev
```

## Configuration

Set these environment variables:

- `AWS_ACCESS_KEY_ID` - S3 access key
- `AWS_SECRET_ACCESS_KEY` - S3 secret key
- `AWS_ENDPOINT_URL` - VersityGW endpoint (e.g., `http://versitygw:7070`)
- `BUCKET_NAME` - S3 bucket name (e.g., `aas-files`)
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8080`)

## API Endpoints

### Health Check
```
GET /health
```

### List Files
```
GET /files?prefix=&max_keys=1000
```

Query parameters:
- `prefix` - Filter files by prefix (optional)
- `max_keys` - Maximum files to return, 1-1000 (default: 1000)

Response:
```json
[
  {
    "key": "path/to/file.txt",
    "size": 1024,
    "last_modified": "2025-12-03T15:30:00",
    "etag": "abc123"
  }
]
```

## Development

Run locally:
```bash
export AWS_ACCESS_KEY_ID=admin
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_ENDPOINT_URL=http://localhost:7070
export BUCKET_NAME=aas-files

make init
make dev
```

Test:
```bash
curl http://localhost:8080/health
curl http://localhost:8080/files
```

## Docker

Build:
```bash
make build
```

Run:
```bash
docker run -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=admin \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e AWS_ENDPOINT_URL=http://versitygw:7070 \
  -e BUCKET_NAME=aas-files \
  file-api:latest
```
