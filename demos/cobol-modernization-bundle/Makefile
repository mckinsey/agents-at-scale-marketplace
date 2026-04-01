.PHONY: help build build-data-seeder install install-with-argo uninstall cobol-demo upload-data delete-data-seeder-job clean

NAMESPACE ?= default
RELEASE_NAME ?= cobol-modernization-bundle
SPEECH_MCP_IMAGE ?= speech-mcp-server:latest
DATA_SEEDER_IMAGE ?= cobol-demo-data-seeder:latest
DATA_SEEDER_ENABLED ?= true
# Set to true to skip installing file-gateway and use the one already in the namespace (e.g. from KYC demo)
USE_EXISTING_FILE_GATEWAY ?= false
# Set to 1 to skip 'helm dependency build' (use if it hangs at "Deleting outdated charts"; run it once manually first)
SKIP_DEP_BUILD ?= 0
FILE_GATEWAY_SKIP_FLAGS := --set file-gateway.fileApi.enabled=false --set file-gateway.filesystemMcp.enabled=false --set file-gateway.versitygw.enabled=false --set file-gateway.versitygw.createSecret=false --set file-gateway.storage.enabled=false --set file-gateway.httpRoute.enabled=false --set file-gateway.fileApi.enabled=false --set file-gateway.filesystemMcp.enabled=false --set file-gateway.versitygw.enabled=false --set file-gateway.versitygw.createSecret=false --set file-gateway.storage.enabled=false --set file-gateway.httpRoute.enabled=false
ifeq ($(USE_EXISTING_FILE_GATEWAY),true)
FILE_GATEWAY_SKIP := $(FILE_GATEWAY_SKIP_FLAGS)
else
FILE_GATEWAY_SKIP :=
endif

help:
	@echo "COBOL Modernization Demo Bundle"
	@echo ""
	@echo "Namespace: $(NAMESPACE) (override with NAMESPACE=my-ns; omit for default)"
	@echo ""
	@echo "Required steps (prerequisite: create a Model in target namespace for agents):"
	@echo "  make uninstall            Remove bundle and file-gateway (run first for a clean install)"
	@echo "  make build                Build speech-mcp-server Docker image (auto-loads into minikube)"
	@echo "  make build-data-seeder    Build data-seeder image (only needed for Option A: automatic upload on install)"
	@echo "  make install              Install bundle (agents + file-gateway)"
	@echo "  make install-with-argo    Install bundle (agents + file-gateway + WorkflowTemplate)"
	@echo "  make upload-data          Upload sample COBOL files and audio (Option B or re-upload)"
	@echo "  make cobol-demo           Run COBOL modernization workflow"
	@echo "  make delete-data-seeder-job  Delete the data-seeder Job (e.g. before testing Option B)"
	@echo ""
	@echo "Use USE_EXISTING_FILE_GATEWAY=true if file-gateway is already in the namespace (e.g. from KYC)."
	@echo "Use SKIP_DEP_BUILD=1 if install hangs at 'Deleting outdated charts' (run 'helm dependency build chart/' once manually first)."
	@echo ""
	@echo "Quick Start Option A: make uninstall && make build-data-seeder && make build && make install-with-argo && make cobol-demo"
	@echo "Quick Start Option B: make uninstall && make build && make install-with-argo DATA_SEEDER_ENABLED=false && make upload-data && make cobol-demo"

build:
	@echo "Building speech-mcp-server image..."
	@docker build -t $(SPEECH_MCP_IMAGE) ../../mcps/speech-mcp-server/
	@echo "Done. Image: $(SPEECH_MCP_IMAGE)"
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Detected minikube - loading image into cluster..."; \
		minikube image load $(SPEECH_MCP_IMAGE); \
		echo "Image loaded into minikube."; \
	fi

install:
	@echo "Installing COBOL Modernization Bundle into namespace: $(NAMESPACE)"
	@echo "Building Helm dependencies..."
	@if [ "$(SKIP_DEP_BUILD)" = "1" ]; then echo "Skipping helm dependency build (SKIP_DEP_BUILD=1)"; else helm dependency build chart/; fi
	@SKIP="$(FILE_GATEWAY_SKIP)"; \
	if [ -z "$$SKIP" ] && kubectl get serviceaccount file-gateway-file-api -n $(NAMESPACE) --request-timeout=10s 2>/dev/null | grep -q file-gateway-file-api; then \
		SKIP="$(FILE_GATEWAY_SKIP_FLAGS)"; \
		echo "Detected existing file-gateway in namespace - skipping file-gateway install"; \
	fi; \
	echo "Installing/upgrading release (this may take 1–2 minutes)..."; \
	helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		$$SKIP \
		--wait
	@echo "Applying namespace discovery labels..."
	@if [ "$(NAMESPACE)" = "default" ]; then \
		kubectl label namespace default ark.mckinsey.com/demo=true --overwrite 2>/dev/null || true; \
		kubectl annotate namespace default ark.mckinsey.com/demo-name="COBOL Modernization" ark.mckinsey.com/demo-description="COBOL modernization with agents for reverse engineering, pseudocode generation, Python conversion, and documentation" --overwrite 2>/dev/null || true; \
	else \
		echo "Namespace $(NAMESPACE) created/labeled by chart."; \
	fi
	@echo "Done. Agents and file-gateway are now available."
	@echo ""
	@echo "Installed agents:"
	@kubectl get agents -n $(NAMESPACE) -l bundle=cobol-modernization

install-with-argo: build
	@echo "Installing COBOL Modernization Bundle with Argo support into namespace: $(NAMESPACE)"
	@echo "Building Helm dependencies..."
	@if [ "$(SKIP_DEP_BUILD)" = "1" ]; then echo "Skipping helm dependency build (SKIP_DEP_BUILD=1)"; else helm dependency build chart/; fi
	@echo "Checking for existing file-gateway..."
	@SKIP="$(FILE_GATEWAY_SKIP)"; NO_HOOKS=""; \
	if [ -z "$$SKIP" ] && kubectl get serviceaccount file-gateway-file-api -n $(NAMESPACE) --request-timeout=10s 2>/dev/null | grep -q file-gateway-file-api; then \
		SKIP="$(FILE_GATEWAY_SKIP_FLAGS)"; \
		NO_HOOKS="--no-hooks"; \
		echo "Detected existing file-gateway in namespace - skipping file-gateway install (hooks skipped; run make upload-data to upload sample data)"; \
	fi; \
	if [ "$(DATA_SEEDER_ENABLED)" = "false" ]; then \
		NO_HOOKS="--no-hooks"; \
		echo "Data seeder disabled - hooks skipped; run make upload-data to upload sample data"; \
	fi; \
	[ -n "$$NO_HOOKS" ] || true; \
	echo "Installing/upgrading release (this may take 1–2 minutes)..."; \
	helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--set dataSeeder.enabled=$(DATA_SEEDER_ENABLED) \
		$$SKIP $$NO_HOOKS \
		--wait
	@echo "Applying namespace discovery labels..."
	@if [ "$(NAMESPACE)" = "default" ]; then \
		kubectl label namespace default ark.mckinsey.com/demo=true --overwrite 2>/dev/null || true; \
		kubectl annotate namespace default ark.mckinsey.com/demo-name="COBOL Modernization" ark.mckinsey.com/demo-description="COBOL modernization with agents for reverse engineering, pseudocode generation, Python conversion, and documentation" --overwrite 2>/dev/null || true; \
	else \
		echo "Namespace $(NAMESPACE) created/labeled by chart."; \
	fi
	@echo ""
	@echo "Done! Installed:"
	@echo "  ✓ Speech MCP Server (Whisper audio transcription)"
	@echo "  ✓ Agents (pseudocode-generator, python-modernizer, audio-transcriber, diagram-creator)"
	@echo "  ✓ File-gateway with MCP tools"
	@echo "  ✓ Argo Workflows RBAC + ServiceAccount"
	@echo "  ✓ WorkflowTemplate (visible in ARK Dashboard)"
	@echo ""
	@echo "Run 'make upload-data' to upload sample data (or if using Option A, data-seeder hook may have already run)."
	@echo ""

delete-data-seeder-job:
	@echo "Deleting data-seeder Job (if present)..."
	@kubectl delete job data-seeder -n $(NAMESPACE) 2>/dev/null && echo "Deleted." || echo "No data-seeder job found (already deleted or not installed)."

uninstall:
	@echo "Uninstalling COBOL Modernization Bundle..."
	@kubectl delete workflowtemplate cobol-modernization-template -n $(NAMESPACE) 2>/dev/null || true
	@helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null || true
	@echo "Removing file-gateway (and related MCP resources) for a clean next install..."
	@kubectl delete deployment,service,serviceaccount,secret,pvc -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found --timeout=60s 2>/dev/null || true
	@kubectl delete httproute -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found 2>/dev/null || true
	@kubectl delete mcpserver -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found 2>/dev/null || true
	@kubectl delete job data-seeder -n $(NAMESPACE) --ignore-not-found 2>/dev/null || true
	@echo "Done. Next install will deploy a fresh file-gateway (no 'existing file-gateway' skip)."

upload-data:
	@echo "Uploading sample COBOL files to file-gateway (via File API, same as data-seeder)..."
	@echo "Waiting for file-gateway-api to be ready..."
	@kubectl rollout status deployment/file-gateway-file-api -n $(NAMESPACE) --timeout=120s 2>/dev/null || true
	@echo "Starting port-forward to file-gateway-api..."
	@(kubectl port-forward -n $(NAMESPACE) svc/file-gateway-api 8181:80 > /dev/null 2>&1 &) && \
	sleep 3 && \
	curl -sf http://localhost:8181/health > /dev/null || (echo "Error: file-gateway-api not reachable"; pkill -f "port-forward.*file-gateway-api" 2>/dev/null; exit 1) && \
	echo "Uploading COBOL files..." && \
	for file in examples/data/cobol-source/*.cbl; do \
		[ -f "$$file" ] || continue; \
		echo "  → $$(basename $$file)"; \
		curl -sf -X POST http://localhost:8181/files -F "file=@$$file" -F "prefix=cobol-source/" > /dev/null || (pkill -f "port-forward.*file-gateway-api" 2>/dev/null; exit 1); \
	done && \
	echo "  → carddemo-interview.m4a" && \
	curl -sf -X POST http://localhost:8181/files \
		-F "file=@examples/data/cobol-source/carddemo-interview.m4a" \
		-F "prefix=cobol-source/" > /dev/null || (pkill -f "port-forward.*file-gateway-api" 2>/dev/null; exit 1) && \
	pkill -f "port-forward.*file-gateway-api" 2>/dev/null || true && \
	echo "Done. Sample data uploaded; visible in ARK Dashboard → Files (cobol-source/)."

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
	