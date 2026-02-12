#!/bin/bash

# ubo-pdf-tools MCP Server Build Script

set -e

IMAGE_TAG=${1:-latest}
TARGET_CLUSTER=${2:-auto}
IMAGE_NAME="ubo-pdf-tools"

echo "Building ubo-pdf-tools MCP Server..."
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Target cluster: ${TARGET_CLUSTER}"

# Build the Docker image
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag and push based on target cluster
case $TARGET_CLUSTER in
    "auto")
        echo "Auto-detecting cluster configuration..."
        # Try to detect if we're in a local development environment
        if kubectl config current-context | grep -E "(kind|minikube|docker-desktop)" > /dev/null 2>&1; then
            echo "Local development cluster detected, loading image locally..."
            
            # Load image into kind if available
            if command -v kind > /dev/null 2>&1 && kind get clusters > /dev/null 2>&1; then
                echo "Loading image into kind cluster..."
                kind load docker-image ${IMAGE_NAME}:${IMAGE_TAG}
            fi
            
            # Load image into minikube if available
            if command -v minikube > /dev/null 2>&1 && minikube status > /dev/null 2>&1; then
                echo "Loading image into minikube..."
                minikube image load ${IMAGE_NAME}:${IMAGE_TAG}
            fi
        else
            echo "Remote cluster detected, pushing to registry..."
            docker push ${IMAGE_NAME}:${IMAGE_TAG}
        fi
        ;;
    "local"|"kind"|"minikube")
        echo "Loading image into local cluster..."
        
        if [[ $TARGET_CLUSTER == "kind" ]] && command -v kind > /dev/null 2>&1; then
            kind load docker-image ${IMAGE_NAME}:${IMAGE_TAG}
        elif [[ $TARGET_CLUSTER == "minikube" ]] && command -v minikube > /dev/null 2>&1; then
            minikube image load ${IMAGE_NAME}:${IMAGE_TAG}
        else
            echo "Local cluster tools not available, skipping image load"
        fi
        ;;
    "remote"|"registry")
        echo "Pushing image to registry..."
        docker push ${IMAGE_NAME}:${IMAGE_TAG}
        ;;
    *)
        echo "Unknown target cluster: $TARGET_CLUSTER"
        echo "Valid options: auto, local, kind, minikube, remote, registry"
        exit 1
        ;;
esac

echo "ubo-pdf-tools MCP Server build completed successfully!"
echo ""
echo "Next steps:"
echo "1. Install the Helm chart:"
{{- if .Values.requiresAuth }}
echo "   make install AUTH_TOKEN=your-auth-token"
{{- else }}
echo "   make install"
{{- end }}
echo "2. Check the status:"
echo "   make status"
echo "3. View logs:"
echo "   make logs"