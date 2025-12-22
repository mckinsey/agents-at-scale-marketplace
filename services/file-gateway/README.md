# File Gateway

A file management system providing S3 file operations through a REST API and web UI.

## Services

### File API (FastAPI Backend)
FastAPI REST service for S3 file operations via VersityGW. Provides endpoints for listing, uploading, downloading, and deleting files from S3-compatible storage.

**Port:** 8080

### VersityGW (S3 Gateway)
S3-compatible gateway for object storage, providing the underlying storage backend.

**Port:** 7070

## Development

For local development, forward port 8080 to access the file gateway API:

```bash
kubectl port-forward -n <namespace> deployment/file-gateway-file-api 8080:8080
```

Use the ark-dashboard to access files.
