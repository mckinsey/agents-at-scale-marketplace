# ubo-pdf-tools MCP Server Makefile

# Variables
IMAGE_NAME ?= ubo-pdf-tools
IMAGE_TAG ?= latest
TARGET_CLUSTER ?= auto
HELM_RELEASE_NAME ?= ubo-pdf-tools-mcp

# Docker image build
.PHONY: build
build:
	@echo "Building ubo-pdf-tools MCP Server Docker image..."
	./build.sh $(IMAGE_TAG) $(TARGET_CLUSTER)

{{- if .Values.requiresAuth }}
# Install using Helm
.PHONY: install
install:
	@echo "Installing ubo-pdf-tools MCP Server with Helm..."
	@if [ -z "$(AUTH_TOKEN)" ]; then \
		echo "Error: AUTH_TOKEN environment variable is required"; \
		echo "Usage: make install AUTH_TOKEN=your-auth-token"; \
		exit 1; \
	fi
	helm install $(HELM_RELEASE_NAME) ./chart \
		--set auth.token="$(AUTH_TOKEN)"
{{- else }}
# Install using Helm
.PHONY: install
install:
	@echo "Installing ubo-pdf-tools MCP Server with Helm..."
	helm install $(HELM_RELEASE_NAME) ./chart
{{- end }}

# Install with values file
.PHONY: install-with-values
install-with-values:
	@echo "Installing ubo-pdf-tools MCP Server with values file..."
	@if [ -z "$(VALUES_FILE)" ]; then \
		echo "Error: VALUES_FILE is required"; \
		echo "Usage: make install-with-values VALUES_FILE=example-values.yaml"; \
		exit 1; \
	fi
	helm install $(HELM_RELEASE_NAME) ./chart \
		--values $(VALUES_FILE)

# Upgrade using Helm
.PHONY: upgrade
upgrade:
	@echo "Upgrading ubo-pdf-tools MCP Server with Helm..."
{{- if .Values.requiresAuth }}
	@if [ -n "$(AUTH_TOKEN)" ]; then \
		helm upgrade $(HELM_RELEASE_NAME) ./chart \
			--set auth.token="$(AUTH_TOKEN)"; \
	elif [ -n "$(VALUES_FILE)" ]; then \
		helm upgrade $(HELM_RELEASE_NAME) ./chart \
			--values $(VALUES_FILE); \
	else \
		helm upgrade $(HELM_RELEASE_NAME) ./chart; \
	fi
{{- else }}
	@if [ -n "$(VALUES_FILE)" ]; then \
		helm upgrade $(HELM_RELEASE_NAME) ./chart \
			--values $(VALUES_FILE); \
	else \
		helm upgrade $(HELM_RELEASE_NAME) ./chart; \
	fi
{{- end }}

# Uninstall using Helm
.PHONY: uninstall
uninstall:
	@echo "Uninstalling ubo-pdf-tools MCP Server..."
	helm uninstall $(HELM_RELEASE_NAME)

# Check status
.PHONY: status
status:
	@echo "Checking ubo-pdf-tools MCP Server status..."
	@echo "=== Helm Release Status ==="
	helm status $(HELM_RELEASE_NAME)
	@echo ""
	@echo "=== Pod Status ==="
	kubectl get pods -l app.kubernetes.io/name=ubo-pdf-tools
	@echo ""
	@echo "=== Service Status ==="
	kubectl get svc -l app.kubernetes.io/name=ubo-pdf-tools
	@echo ""
	@echo "=== MCP Server Status ==="
	kubectl get mcpservers -l app.kubernetes.io/name=ubo-pdf-tools

# Show logs
.PHONY: logs
logs:
	@echo "Showing ubo-pdf-tools MCP Server logs..."
	kubectl logs -l app.kubernetes.io/name=ubo-pdf-tools --follow

# Deploy examples
.PHONY: deploy-examples
deploy-examples:
	@echo "Deploying example agent and query..."
	kubectl apply -f examples/

# Clean up examples
.PHONY: clean-examples
clean-examples:
	@echo "Cleaning up example resources..."
	kubectl delete -f examples/ --ignore-not-found

# Test the MCP server
.PHONY: test
test:
	@echo "Testing ubo-pdf-tools MCP Server..."
{{- if .Values.technology }}
{{- if eq .Values.technology "node" }}
	npm test
{{- else if eq .Values.technology "python" }}
	python -m pytest
{{- else if eq .Values.technology "go" }}
	go test ./...
{{- else if eq .Values.technology "deno" }}
	deno test
{{- end }}
{{- else }}
	@echo "No tests configured for this MCP server"
{{- end }}

# Development server
.PHONY: dev
dev:
	@echo "Starting ubo-pdf-tools MCP Server in development mode..."
{{- if .Values.technology }}
{{- if eq .Values.technology "node" }}
	npm run dev
{{- else if eq .Values.technology "python" }}
	python main.py
{{- else if eq .Values.technology "go" }}
	go run .
{{- else if eq .Values.technology "deno" }}
	deno run -A index.ts
{{- end }}
{{- else }}
	@echo "Development mode not configured for this MCP server"
{{- end }}

# Port forward for local testing
.PHONY: port-forward
port-forward:
	@echo "Port forwarding ubo-pdf-tools MCP Server to localhost:8080..."
	kubectl port-forward svc/$(HELM_RELEASE_NAME) 8080:8080

# Help
.PHONY: help
help:
	@echo "ubo-pdf-tools MCP Server Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  build              Build Docker image"
	@echo "  install            Install with Helm"
	@echo "  install-with-values Install with values file"
	@echo "  upgrade            Upgrade with Helm"
	@echo "  uninstall          Uninstall from cluster"
	@echo "  status             Check deployment status"
	@echo "  logs               Show pod logs"
	@echo "  deploy-examples    Deploy example resources"
	@echo "  clean-examples     Clean up example resources"
	@echo "  test               Run tests"
	@echo "  dev                Start development server"
	@echo "  port-forward       Port forward to localhost"
	@echo "  help               Show this help"
	@echo ""
{{- if .Values.requiresAuth }}
	@echo "Environment variables:"
	@echo "  AUTH_TOKEN         Authentication token (required for install)"
	@echo "  VALUES_FILE        Helm values file path"
	@echo ""
{{- end }}
	@echo "Examples:"
{{- if .Values.requiresAuth }}
	@echo "  make install AUTH_TOKEN=your-token"
{{- else }}
	@echo "  make install"
{{- end }}
	@echo "  make install-with-values VALUES_FILE=example-values.yaml"
	@echo "  make upgrade"
	@echo "  make status"