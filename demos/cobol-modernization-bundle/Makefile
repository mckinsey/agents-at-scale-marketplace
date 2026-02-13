.PHONY: help build build-data-seeder install install-with-argo uninstall cobol-demo upload-data clean

NAMESPACE ?= cobol-demo
RELEASE_NAME ?= cobol-modernization-bundle
SPEECH_MCP_IMAGE ?= speech-mcp-server:latest
DATA_SEEDER_IMAGE ?= cobol-demo-data-seeder:latest

help:
	@echo "COBOL Modernization Demo Bundle"
	@echo ""
	@echo "Available commands:"
	@echo "  make build              Build speech-mcp-server Docker image (auto-loads into minikube)"
	@echo "  make install            Install bundle (agents + file-gateway)"
	@echo "  make install-with-argo  Install everything (bundle + WorkflowTemplate)"
	@echo "  make upload-data        Upload sample COBOL files and audio"
	@echo "  make cobol-demo         Run COBOL modernization workflow"
	@echo "  make uninstall          Remove bundle and cleanup"
	@echo ""
	@echo "Quick Start:"
	@echo "  make build && make install-with-argo && make upload-data && make cobol-demo"

build: build-data-seeder
	@echo "Building speech-mcp-server image..."
	@docker build -t $(SPEECH_MCP_IMAGE) ../../mcps/speech-mcp-server/
	@echo "Done. Image: $(SPEECH_MCP_IMAGE)"
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Detected minikube - loading image into cluster..."; \
		minikube image load $(SPEECH_MCP_IMAGE); \
		echo "Image loaded into minikube."; \
	fi

install:
	@echo "Installing COBOL Modernization Bundle..."
	@echo "Building Helm dependencies..."
	@helm dependency build chart/
	@helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait
	@echo "Applying namespace discovery labels..."
	@kubectl apply -f ../namespaces/cobol-demo.yaml
	@echo "Done. Agents and file-gateway are now available."
	@echo ""
	@echo "Installed agents:"
	@kubectl get agents -n $(NAMESPACE) -l bundle=cobol-modernization

install-with-argo: build
	@echo "Installing COBOL Modernization Bundle with Argo support..."
	@echo "Building Helm dependencies..."
	@helm dependency build chart/
	@helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait
	@echo "Applying namespace discovery labels..."
	@kubectl apply -f ../namespaces/cobol-demo.yaml
	@echo ""
	@echo "Done! Installed:"
	@echo "  ✓ Speech MCP Server (Whisper audio transcription)"
	@echo "  ✓ Agents (pseudocode-generator, python-modernizer, audio-transcriber, diagram-creator)"
	@echo "  ✓ File-gateway with MCP tools"
	@echo "  ✓ Argo Workflows RBAC + ServiceAccount"
	@echo "  ✓ WorkflowTemplate (visible in ARK Dashboard)"

uninstall:
	@echo "Uninstalling COBOL Modernization Bundle..."
	@kubectl delete workflowtemplate cobol-modernization-template -n $(NAMESPACE) 2>/dev/null || true
	@helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete rolebinding argo-workflow-cobol-mod-access -n $(NAMESPACE) 2>/dev/null || true
	@echo "Done."

upload-data:
	@echo "Uploading sample COBOL files to file-gateway..."
	@echo "Creating directory structure..."
	@kubectl exec -n $(NAMESPACE) deployment/file-gateway-filesystem-mcp -- mkdir -p \
		/data/aas-files/cobol-source \
		/data/aas-files/output/pseudocode \
		/data/aas-files/output/transcription \
		/data/aas-files/output/diagrams \
		/data/aas-files/output/python
	@echo "Starting port-forward to file-gateway API..."
	@(kubectl port-forward -n $(NAMESPACE) svc/file-gateway-api 8181:80 > /dev/null 2>&1 &) && \
	sleep 4 && \
	echo "Testing connection..." && \
	curl -s http://localhost:8181/health > /dev/null && \
	echo "Uploading COBOL files..." && \
	for file in examples/data/cobol-source/*.cbl; do \
		echo "  Uploading $$(basename $$file)..." && \
		curl -s -X POST http://localhost:8181/files \
			-F "file=@$$file" \
			-F "prefix=cobol-source/" > /dev/null; \
	done && \
	echo "Uploading audio file..." && \
	curl -s -X POST http://localhost:8181/files \
		-F "file=@examples/data/cobol-source/carddemo-interview.m4a" \
		-F "prefix=cobol-source/" > /dev/null && \
	pkill -f "port-forward.*file-gateway-api" > /dev/null 2>&1 && \
	echo "" && \
	echo "Done. Sample data uploaded successfully." && \
	echo "Files available at: cobol-source/"

cobol-demo:
	@echo "Submitting COBOL modernization workflow..."
	@kubectl create -f examples/cobol-modernization-from-template.yaml -n $(NAMESPACE)
	@echo ""
	@echo "Done. Monitor with:"
	@echo "  kubectl get workflows -n $(NAMESPACE) -w"
	@echo ""
	@echo "Or view in ARK Dashboard → Argo Workflows"

build-data-seeder:
	@echo "Building data-seeder image..."
	@docker build -t $(DATA_SEEDER_IMAGE) examples/data/
	@echo "Done. Image: $(DATA_SEEDER_IMAGE)"
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Detected minikube - loading image into cluster..."; \
		minikube image load $(DATA_SEEDER_IMAGE); \
		echo "Image loaded into minikube."; \
	fi

clean:
	@echo "Cleaning up workflow artifacts..."
	@kubectl delete workflows -n $(NAMESPACE) -l use-case=cobol-modernization 2>/dev/null || true
	@kubectl delete queries -n $(NAMESPACE) -l use-case=cobol-modernization 2>/dev/null || true
	@echo "Done."
