.PHONY: help build build-filesystem build-pdf-mcp build-web-mcp build-perplexity-mcp build-companies-house-mcp build-mcps install install-with-argo upgrade uninstall submit-profile-init submit-profile-enrichment submit-requirements submit-initial-risk submit-ownership submit-entities submit-controllers submit-purpose submit-media submit-blacklist submit-profile-finalization submit-kyc-memo upload-data build-data-seeder delete-data-seeder-job clean verify-mcp wait-for-tools ready verify-agents

NAMESPACE ?= $(or $(K8S_NAMESPACE),default)
MCP_SOURCE_NAMESPACE ?= $(or $(MCP_NAMESPACE),default)
RELEASE_NAME ?= kyc-onboarding-bundle
FILESYSTEM_MCP_IMAGE ?= filesystem-mcp-server:latest
PDF_EXTRACTION_MCP_IMAGE ?= pdf-extraction-mcp:latest
COMPANIES_HOUSE_MCP_IMAGE ?= companies-house-mcp:latest
WEB_RESEARCH_MCP_IMAGE ?= web-research-mcp:latest
PERPLEXITY_ASK_MCP_IMAGE ?= perplexity-ask-mcp:latest
DATA_SEEDER_IMAGE ?= kyc-demo-data-seeder
DATA_SEEDER_ENABLED ?= true
USE_EXISTING_FILE_GATEWAY ?= false
SKIP_DEP_BUILD ?= 0
FILE_GATEWAY_SKIP_FLAGS := --set file-gateway.fileApi.enabled=false --set file-gateway.filesystemMcp.enabled=false --set file-gateway.versitygw.enabled=false --set file-gateway.versitygw.createSecret=false --set file-gateway.storage.enabled=false --set file-gateway.httpRoute.enabled=false --set file-gateway.fileApi.enabled=false --set file-gateway.filesystemMcp.enabled=false --set file-gateway.versitygw.enabled=false --set file-gateway.versitygw.createSecret=false --set file-gateway.storage.enabled=false --set file-gateway.httpRoute.enabled=false
ifeq ($(USE_EXISTING_FILE_GATEWAY),true)
FILE_GATEWAY_SKIP := $(FILE_GATEWAY_SKIP_FLAGS)
else
FILE_GATEWAY_SKIP :=
endif

help:
	@echo "KYC Onboarding Bundle — Namespace: $(NAMESPACE)"
	@echo ""
	@echo "Setup:"
	@echo "  make uninstall              Remove bundle and file-gateway"
	@echo "  make install-with-argo      Install bundle + WorkflowTemplates"
	@echo "  make install                Install bundle (without WorkflowTemplates)"
	@echo "  make upgrade                Upgrade bundle (auto-detects existing file-gateway)"
	@echo "  make build                  Deploy all MCPs (filesystem + pdf + web + perplexity + companies-house)"
	@echo "  make build-data-seeder      Build data-seeder image (Option A)"
	@echo "  make upload-data            Upload sample data to file-gateway (Option B)"
	@echo ""
	@echo "Individual MCPs:"
	@echo "  make build-filesystem       Filesystem MCP only"
	@echo "  make build-pdf-mcp          PDF extraction MCP only"
	@echo "  make build-web-mcp          Web research MCP only"
	@echo "  make build-perplexity-mcp   Perplexity Ask MCP only"
	@echo "  make build-companies-house-mcp  Companies House MCP only"
	@echo ""
	@echo "Workflows:"
	@echo "  Phase I:  submit-profile-init, submit-profile-enrichment, submit-requirements, submit-initial-risk"
	@echo "  Phase II: submit-ownership, submit-entities, submit-controllers, submit-purpose, submit-media, submit-blacklist"
	@echo "  Profile:  submit-profile-finalization   Phase III: submit-kyc-memo"
	@echo ""
	@echo "Verify:"
	@echo "  make ready                  Full readiness check (MCP + tools)"
	@echo "  make verify-mcp             Check MCPServer and Tool CRs"
	@echo "  make verify-agents          List agents (expects 21)"
	@echo "  make wait-for-tools         Wait for Tool CRs to be created"
	@echo "  make clean                  Remove workflow artifacts"
	@echo "  make delete-data-seeder-job Delete data-seeder Job"
	@echo ""
	@echo "Quick Start A: make uninstall && make build-data-seeder && make install-with-argo && make build && make ready"
	@echo "Quick Start B: make uninstall && make install-with-argo DATA_SEEDER_ENABLED=false && make build && make upload-data && make ready"

build-filesystem:
	@echo "Building filesystem MCP server image..."
	@docker build -t $(FILESYSTEM_MCP_IMAGE) ../../mcps/filesystem-mcp-server/
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Loading image into minikube..."; \
		minikube image load $(FILESYSTEM_MCP_IMAGE); \
	fi
	@echo "Waiting for PVC file-gateway-storage to be Bound..."
	@if ! kubectl get pvc file-gateway-storage -n $(NAMESPACE) --request-timeout=5s 2>/dev/null | grep -q file-gateway-storage; then \
		echo "PVC not found — creating it..."; \
		( echo 'apiVersion: v1'; echo 'kind: PersistentVolumeClaim'; echo 'metadata:'; echo '  name: file-gateway-storage'; echo 'spec:'; echo '  accessModes:'; echo '    - ReadWriteOnce'; echo '  resources:'; echo '    requests:'; echo '      storage: 1Gi' ) | kubectl apply -n $(NAMESPACE) -f -; \
	fi
	@kubectl wait --for=jsonpath='{.status.phase}=Bound' pvc/file-gateway-storage -n $(NAMESPACE) --timeout=120s 2>/dev/null || \
		(echo "Error: PVC not Bound. Run 'make install' first, then 'make build'."; exit 1)
	@echo "Deploying filesystem MCP server..."
	@helm template mcp-filesystem ../../mcps/filesystem-mcp-server/chart \
		--namespace $(NAMESPACE) \
		--set persistence.existingClaim=file-gateway-storage \
		--set env.BASE_DATA_DIR=/data/aas-files \
		--set image.repository=filesystem-mcp-server \
		--set image.tag=latest \
		--set image.pullPolicy=IfNotPresent \
		--set podSecurityContext.runAsUser=1000 \
		--set podSecurityContext.fsGroup=1000 \
		| kubectl apply -f - -n $(NAMESPACE)
	@echo "Done."

build-pdf-mcp:
	@echo "Building pdf-extraction MCP image..."
	@docker build -t $(PDF_EXTRACTION_MCP_IMAGE) ../../mcps/pdf-extraction-mcp/
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Loading image into minikube..."; \
		minikube image load $(PDF_EXTRACTION_MCP_IMAGE); \
	fi
	@echo "Deploying pdf-extraction MCP..."
	@helm template pdf-extraction-mcp ../../mcps/pdf-extraction-mcp/chart \
		--namespace $(NAMESPACE) \
		--set image.repository=pdf-extraction-mcp \
		--set image.tag=latest \
		--set image.pullPolicy=IfNotPresent \
		| kubectl apply -f - -n $(NAMESPACE)
	@echo "Done."

build-companies-house-mcp:
	@echo "Building companies-house MCP image..."
	@docker build -t $(COMPANIES_HOUSE_MCP_IMAGE) ../../mcps/companies-house-mcp/
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Loading image into minikube..."; \
		minikube image load $(COMPANIES_HOUSE_MCP_IMAGE); \
	fi
	@echo "Deploying companies-house MCP..."
	@sed 's/namespace: default/namespace: $(NAMESPACE)/g' ../../mcps/companies-house-mcp/k8s-deployment.yaml | kubectl apply -f - -n $(NAMESPACE)
	@echo "Done."
	@echo "NOTE: Create API key secret with: kubectl create secret generic companies-house-api-key --from-literal=api-key=YOUR_KEY"

build-web-mcp:
	@echo "Building web-research MCP image..."
	@docker build -t $(WEB_RESEARCH_MCP_IMAGE) ../../mcps/web-research-mcp/
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Loading image into minikube..."; \
		minikube image load $(WEB_RESEARCH_MCP_IMAGE); \
	fi
	@echo "Deploying web-research MCP..."
	@sed 's/namespace: default/namespace: $(NAMESPACE)/g' ../../mcps/web-research-mcp/k8s-deployment.yaml | kubectl apply -f - -n $(NAMESPACE)
	@echo "Done."

build-perplexity-mcp:
	@echo "Building perplexity-ask MCP image..."
	@docker build -t $(PERPLEXITY_ASK_MCP_IMAGE) ../../mcps/perplexity-ask-mcp/
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Loading image into minikube..."; \
		minikube image load $(PERPLEXITY_ASK_MCP_IMAGE); \
	fi
	@echo "Deploying perplexity-ask MCP..."
	@sed 's/namespace: default/namespace: $(NAMESPACE)/g' ../../mcps/perplexity-ask-mcp/k8s-deployment.yaml | kubectl apply -f - -n $(NAMESPACE)
	@echo "Done."

build: build-filesystem build-pdf-mcp build-web-mcp build-perplexity-mcp build-companies-house-mcp
	@echo ""
	@echo "All MCPs deployed. Run 'make ready' to verify."

build-mcps: build

install:
	@echo "Installing KYC Onboarding Bundle into namespace: $(NAMESPACE)"
	@if [ "$(SKIP_DEP_BUILD)" = "1" ]; then echo "Skipping helm dependency build"; else helm dependency build chart/; fi
	@SKIP="$(FILE_GATEWAY_SKIP)"; \
	if [ -z "$$SKIP" ] && kubectl get serviceaccount file-gateway-file-api -n $(NAMESPACE) --request-timeout=10s 2>/dev/null | grep -q file-gateway-file-api; then \
		SKIP="$(FILE_GATEWAY_SKIP_FLAGS)"; \
		echo "Detected existing file-gateway — skipping"; \
	fi; \
	if ! helm status $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null; then \
		if kubectl get pvc file-gateway-storage -n $(NAMESPACE) 2>/dev/null; then \
			echo "Removing existing PVC for clean install..."; \
			kubectl delete pvc file-gateway-storage -n $(NAMESPACE) --timeout=60s 2>/dev/null || true; \
		fi; \
	fi; \
	helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		$$SKIP \
		--wait
	@if [ "$(NAMESPACE)" = "default" ]; then \
		kubectl label namespace default ark.mckinsey.com/demo=true --overwrite 2>/dev/null || true; \
		kubectl annotate namespace default ark.mckinsey.com/demo-name="KYC Onboarding" ark.mckinsey.com/demo-description="KYC onboarding workflows with specialized agents and teams for customer due diligence" --overwrite 2>/dev/null || true; \
	fi
	@echo "Done."
	@kubectl get agents -n $(NAMESPACE) -l bundle=kyc-onboarding 2>/dev/null || true
	@kubectl get teams -n $(NAMESPACE) -l bundle=kyc-onboarding 2>/dev/null || true

install-with-argo:
	@echo "Installing KYC Onboarding Bundle into namespace: $(NAMESPACE)"
	@if [ "$(SKIP_DEP_BUILD)" = "1" ]; then echo "Skipping helm dependency build"; else helm dependency build chart/; fi
	@SKIP="$(FILE_GATEWAY_SKIP)"; \
	if [ -z "$$SKIP" ] && kubectl get serviceaccount file-gateway-file-api -n $(NAMESPACE) --request-timeout=10s 2>/dev/null | grep -q file-gateway-file-api; then \
		SKIP="$(FILE_GATEWAY_SKIP_FLAGS)"; \
		NO_HOOKS="--no-hooks"; \
		echo "Detected existing file-gateway — skipping (run make upload-data for sample data)"; \
	fi; \
	if [ "$(DATA_SEEDER_ENABLED)" = "false" ]; then \
		echo "Data seeder disabled — run make upload-data after install"; \
	fi; \
	if ! helm status $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null; then \
		if kubectl get pvc file-gateway-storage -n $(NAMESPACE) 2>/dev/null; then \
			echo "Removing existing PVC for clean install..."; \
			kubectl delete pvc file-gateway-storage -n $(NAMESPACE) --timeout=60s 2>/dev/null || true; \
		fi; \
	fi; \
	[ -n "$$NO_HOOKS" ] || true; \
	echo "Installing (this may take 1-2 minutes)..."; \
	helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--set argoWorkflows.rbac.enabled=true \
		--set dataSeeder.enabled=$(DATA_SEEDER_ENABLED) \
		$$SKIP $$NO_HOOKS \
		--timeout 5m
	@if [ "$(NAMESPACE)" = "default" ]; then \
		kubectl label namespace default ark.mckinsey.com/demo=true --overwrite 2>/dev/null || true; \
		kubectl annotate namespace default ark.mckinsey.com/demo-name="KYC Onboarding" ark.mckinsey.com/demo-description="KYC onboarding workflows with specialized agents and teams for customer due diligence" --overwrite 2>/dev/null || true; \
	fi
	@echo "Waiting for pods..."
	@kubectl wait --for=condition=ready pod -l bundle=kyc-onboarding -n $(NAMESPACE) --timeout=120s || echo "Some pods not ready yet, continuing..."
	@echo ""
	@echo "Done. Run 'make build' to deploy MCPs, then 'make ready' to verify."
	@kubectl get agents -n $(NAMESPACE) -l bundle=kyc-onboarding 2>/dev/null || true
	@kubectl get teams -n $(NAMESPACE) -l bundle=kyc-onboarding 2>/dev/null || true

upgrade:
	@echo "Upgrading KYC Onboarding Bundle in namespace: $(NAMESPACE)"
	@if [ "$(SKIP_DEP_BUILD)" = "1" ]; then echo "Skipping helm dependency build"; else helm dependency build chart/; fi
	@SKIP="$(FILE_GATEWAY_SKIP)"; \
	if [ -z "$$SKIP" ] && kubectl get serviceaccount file-gateway-file-api -n $(NAMESPACE) --request-timeout=10s 2>/dev/null | grep -q file-gateway-file-api; then \
		SKIP="$(FILE_GATEWAY_SKIP_FLAGS)"; \
		echo "Detected existing file-gateway — skipping"; \
	fi; \
	helm upgrade $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		-f chart/values.yaml \
		--set argoWorkflows.rbac.enabled=true \
		--set dataSeeder.enabled=$(DATA_SEEDER_ENABLED) \
		$$SKIP \
		--timeout 5m
	@echo "Upgrade complete."

delete-data-seeder-job:
	@kubectl delete job data-seeder -n $(NAMESPACE) 2>/dev/null && echo "Deleted." || echo "No data-seeder job found."

uninstall:
	@echo "Uninstalling KYC Onboarding Bundle..."
	@helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null || true
	@echo "Removing ARK custom resources..."
	@kubectl delete agents -n $(NAMESPACE) -l bundle=kyc-onboarding --timeout=60s 2>/dev/null || true
	@kubectl delete teams -n $(NAMESPACE) -l bundle=kyc-onboarding --timeout=60s 2>/dev/null || true
	@kubectl delete models -n $(NAMESPACE) -l bundle=kyc-onboarding --timeout=60s 2>/dev/null || true
	@kubectl delete tools -n $(NAMESPACE) -l bundle=kyc-onboarding --timeout=60s 2>/dev/null || true
	@kubectl delete mcpservers -n $(NAMESPACE) -l bundle=kyc-onboarding --timeout=60s 2>/dev/null || true
	@kubectl delete queries -n $(NAMESPACE) -l use-case=kyc-onboarding --timeout=30s 2>/dev/null || true
	@kubectl delete workflows -n $(NAMESPACE) -l use-case=kyc-onboarding --timeout=30s 2>/dev/null || true
	@kubectl delete rolebinding argo-workflow-default-access -n $(NAMESPACE) 2>/dev/null || true
	@echo "Removing MCP servers..."
	@kubectl delete mcpserver pdf-extraction-mcp perplexity web-research-mcp companies-house -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete mcpserver -l app.kubernetes.io/name=mcp-filesystem -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete mcpserver -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@echo "Removing file-gateway and MCP deployments..."
	@kubectl delete deployment -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found --timeout=30s --force --grace-period=0 2>/dev/null || true
	@kubectl delete deployment -l app.kubernetes.io/name=mcp-filesystem -n $(NAMESPACE) --ignore-not-found --timeout=30s --force --grace-period=0 2>/dev/null || true
	@kubectl delete deployment pdf-extraction-mcp web-research-mcp perplexity-ask-mcp -n $(NAMESPACE) --ignore-not-found --timeout=30s --force --grace-period=0 2>/dev/null || true
	@kubectl delete service,serviceaccount,secret -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete service,serviceaccount -l app.kubernetes.io/name=mcp-filesystem -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete service pdf-extraction-mcp web-research-mcp perplexity-ask-mcp -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete serviceaccount pdf-extraction-mcp web-research-mcp perplexity-ask-mcp -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete httproute -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@sleep 3
	@kubectl delete pvc file-gateway-storage -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete pvc -l app.kubernetes.io/name=file-gateway -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@kubectl delete job data-seeder -n $(NAMESPACE) --ignore-not-found --timeout=30s 2>/dev/null || true
	@echo "Done."

# ── Workflow submissions ─────────────────────────────────────────────

submit-profile-init:
	@echo "Submitting profile initialization (Phase I)..."
	@kubectl create -f examples/lx-profile-initialization-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-profile-enrichment:
	@echo "Submitting profile enrichment (Phase I)..."
	@kubectl create -f examples/lx-profile-enrichment-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-requirements:
	@echo "Submitting requirements and standards (Phase I)..."
	@kubectl create -f examples/lx-requirements-and-standards-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-initial-risk:
	@echo "Submitting initial risk assessment (Phase I)..."
	@kubectl create -f examples/lx-initial-risk-assessment-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-ownership:
	@echo "Submitting ownership structure (Phase II)..."
	@kubectl create -f examples/lx-retrieve-ownership-structure-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-entities:
	@echo "Submitting entities & vessels (Phase II)..."
	@kubectl create -f examples/lx-retrieve-entities-vessels-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-controllers:
	@echo "Submitting key controllers (Phase II)..."
	@kubectl create -f examples/lx-retrieve-key-controllers-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-purpose:
	@echo "Submitting purpose of relationship (Phase II)..."
	@kubectl create -f examples/lx-assess-purpose-of-relationship-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-media:
	@echo "Submitting adverse media screening (Phase II)..."
	@kubectl create -f examples/lx-adverse-media-screening-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-blacklist:
	@echo "Submitting blacklist & sanction screening (Phase II)..."
	@kubectl create -f examples/lx-blacklist-sanction-screening-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-profile-finalization:
	@echo "Submitting profile finalization..."
	@kubectl create -f examples/lx-profile-finalization-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

submit-kyc-memo:
	@echo "Submitting KYC memo (Phase III)..."
	@kubectl create -f examples/lx-kyc-memo-from-template.yaml -n $(NAMESPACE)
	@echo "Monitor: kubectl get workflows -n $(NAMESPACE) -w"

# ── Data upload ──────────────────────────────────────────────────────

upload-data:
	@echo "Uploading example data to file-gateway..."
	@kubectl rollout status deployment/file-gateway-file-api -n $(NAMESPACE) --timeout=120s 2>/dev/null || true
	@pkill -f "port-forward.*file-gateway-api" 2>/dev/null || true; sleep 1
	@(kubectl port-forward -n $(NAMESPACE) svc/file-gateway-api 8181:80 > /dev/null 2>&1 &) && \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -sf http://localhost:8181/health > /dev/null 2>&1; then break; fi; \
		if [ $$i -eq 10 ]; then \
			echo "Error: file-gateway-api not reachable after 20s"; \
			pkill -f "port-forward.*file-gateway-api" 2>/dev/null || true; \
			exit 1; \
		fi; \
	done && \
	echo "Uploading files..." && \
	for file in $$(find examples/data -type f ! -name Dockerfile ! -name 'README*' ! -name '.gitignore' ! -path '*.git*'); do \
		rel="$${file#examples/data/}"; \
		dir="$$(dirname "$$rel")"; \
		prefix="source_code_files/$$dir/"; \
		echo "  -> $$rel"; \
		resp=$$(curl -s -w "\n%{http_code}" --max-time 60 -X POST http://localhost:8181/files -F "file=@$$file" -F "prefix=$$prefix"); \
		code=$$(echo "$$resp" | tail -1); \
		if [ "$$code" != "200" ]; then \
			echo "Upload failed for $$rel (HTTP $${code:-error})"; \
			pkill -f "port-forward.*file-gateway-api" 2>/dev/null || true; \
			exit 1; \
		fi; \
	done && \
	pkill -f "port-forward.*file-gateway-api" 2>/dev/null || true && \
	echo "Done. Data visible in ARK Dashboard -> Files."

build-data-seeder:
	@echo "Building data seeder image..."
	@docker build -t $(DATA_SEEDER_IMAGE):latest examples/data/
	@if kubectl config current-context 2>/dev/null | grep -q minikube; then \
		echo "Loading image into minikube..."; \
		minikube image load $(DATA_SEEDER_IMAGE):latest; \
	fi
	@echo "Done. Image: $(DATA_SEEDER_IMAGE):latest"

# ── Verify & Debug ──────────────────────────────────────────────────

clean:
	@echo "Cleaning up workflow artifacts..."
	@kubectl delete workflows -n $(NAMESPACE) -l use-case=kyc-onboarding 2>/dev/null || true
	@kubectl delete queries -n $(NAMESPACE) -l use-case=kyc-onboarding 2>/dev/null || true
	@echo "Done."

verify-agents:
	@echo "Agents in namespace $(NAMESPACE) (expects 21):"
	@kubectl get agents -n $(NAMESPACE) -l bundle=kyc-onboarding --no-headers 2>/dev/null | wc -l | xargs echo "  Count:"
	@kubectl get agents -n $(NAMESPACE) -l bundle=kyc-onboarding 2>/dev/null || echo "  None found — run make install-with-argo"

verify-mcp:
	@echo "MCPServers:"
	@kubectl get mcpserver mcp-filesystem -n $(NAMESPACE) 2>/dev/null || echo "  mcp-filesystem: NOT FOUND (run make build)"
	@kubectl get mcpserver pdf-extraction-mcp -n $(NAMESPACE) 2>/dev/null || echo "  pdf-extraction-mcp: NOT FOUND (run make build-pdf-mcp)"
	@kubectl get mcpserver web-research-mcp -n $(NAMESPACE) 2>/dev/null || echo "  web-research-mcp: NOT FOUND (run make build-web-mcp)"
	@echo ""
	@echo "Pods:"
	@kubectl get pods -n $(NAMESPACE) -l app.kubernetes.io/name=mcp-filesystem 2>/dev/null || true
	@kubectl get pods -n $(NAMESPACE) -l app=pdf-extraction-mcp 2>/dev/null || true
	@kubectl get pods -n $(NAMESPACE) -l app=web-research-mcp 2>/dev/null || true

wait-for-tools:
	@echo "Waiting for Tool mcp-filesystem-read-file..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24; do \
		if kubectl get tools -n $(NAMESPACE) --request-timeout=5s 2>/dev/null | grep -q mcp-filesystem-read-file; then \
			echo "Found."; \
			exit 0; \
		fi; \
		echo "  ... waiting ($$(( i * 5 ))s)"; \
		sleep 5; \
	done; \
	echo "Timeout after 120s. Run 'make verify-mcp' and check pods are READY."; \
	exit 1

ready: verify-mcp wait-for-tools
	@echo ""
	@echo "Tools ready. Next steps:"
	@echo "  1. Ensure secret default-api-key exists: kubectl get secret default-api-key -n $(NAMESPACE)"
	@echo "  2. Wait 30-60s, refresh ARK Dashboard — agents/teams should show Available"
	@echo "  3. Run: make submit-profile-init (or other workflows)"

