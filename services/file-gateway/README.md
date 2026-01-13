# File Gateway

A file management system providing S3 file operations through a REST API and web UI.

## Services

### File API (FastAPI Backend)
FastAPI REST service for S3 file operations via VersityGW. Provides endpoints for listing, uploading, downloading, and deleting files from S3-compatible storage.

**Port:** 8080

### VersityGW (S3 Gateway)
S3-compatible gateway for object storage, providing the underlying storage backend.

**Port:** 7070

## Deployment

### Deploying to [kind](https://kind.sigs.k8s.io/) clusters

When deploying to Docker Desktop managed kind clusters, the registry-mirror may fail to pull external images. Use the following workaround to load images directly:

#### Build the file-api image

```bash
cd services/file-api
docker build -t file-api:latest .
```

#### Load the image to the cluster

```bash
# Load file-api image
kind load docker-image file-api:latest --name <cluster-name>

# Load busybox for init containers (if kind load fails with multi-platform issues)
docker pull busybox:latest
docker save busybox:latest | docker exec -i <cluster-name>-control-plane ctr --namespace=k8s.io images import -

# Deploy with Helm
helm upgrade --install file-gateway ./chart -n <namespace>
```

**Note**: The `values.yaml` uses `repository: file-api` (without registry prefix). This allows kubernetes to find the locally loaded image in containerd's cache.

## Development

For local development, forward port 8080 to access the file gateway API:

```bash
kubectl port-forward -n <namespace> deployment/file-gateway-file-api 8080:8080
```

Use the ark-dashboard to access files.
