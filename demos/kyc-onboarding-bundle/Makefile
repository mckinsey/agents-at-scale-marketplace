.PHONY: help install install-with-argo setup-namespace uninstall submit-ownership submit-entities submit-controllers submit-purpose submit-media submit-blacklist upload-data

# Load namespace configuration from .env if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

NAMESPACE ?= $(K8S_NAMESPACE)
NAMESPACE ?= kyc-onboarding-demo
MCP_SOURCE_NAMESPACE ?= $(MCP_NAMESPACE)
MCP_SOURCE_NAMESPACE ?= default
RELEASE_NAME ?= kyc-onboarding-bundle

help:
	@echo "KYC Onboarding Bundle"
	@echo ""
	@echo "Available commands:"
	@echo "  make install-with-argo     Install everything (bundle + WorkflowTemplates)"
	@echo "  make setup-namespace       Setup cross-namespace tools and dependencies"
	@echo "  make upload-data           Upload example customer data"
	@echo "  make submit-<workflow>     Submit specific workflow:"
	@echo "    - submit-ownership       Retrieve ownership structure"
	@echo "    - submit-entities        Retrieve entities & vessels"
	@echo "    - submit-controllers     Retrieve key controllers"
	@echo "    - submit-purpose         Assess purpose of relationship"
	@echo "    - submit-media           Adverse media screening"
	@echo "    - submit-blacklist       Blacklist & sanction screening"
	@echo "  make uninstall             Remove bundle and cleanup"

setup-namespace:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "🔧 Setting up namespace: $(NAMESPACE)"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "Using MCP servers from: $(MCP_SOURCE_NAMESPACE)"
	@echo ""
	@# Create namespace if it doesn't exist
	@kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	@# Setup cross-namespace tools
	@echo "📡 Setting up cross-namespace tool references..."
	@../../scripts/setup-tools-for-namespace.sh -s $(MCP_SOURCE_NAMESPACE) -t $(NAMESPACE)
	@# Copy model and secrets if they exist
	@echo ""
	@echo "📦 Copying model and secrets from $(MCP_SOURCE_NAMESPACE)..."
	@if kubectl get model default -n $(MCP_SOURCE_NAMESPACE) &>/dev/null; then \
		kubectl get model default -n $(MCP_SOURCE_NAMESPACE) -o json | \
		jq 'del(.metadata.namespace, .metadata.uid, .metadata.resourceVersion, .metadata.creationTimestamp, .metadata.managedFields)' | \
		kubectl apply -f - -n $(NAMESPACE) 2>&1 | grep -v "Unknown field" || true; \
		echo "   ✅ Copied model: default"; \
	fi
	@if kubectl get secret ai-gateway-azure-openai -n $(MCP_SOURCE_NAMESPACE) &>/dev/null; then \
		kubectl get secret ai-gateway-azure-openai -n $(MCP_SOURCE_NAMESPACE) -o json | \
		jq 'del(.metadata.namespace, .metadata.uid, .metadata.resourceVersion, .metadata.creationTimestamp, .metadata.managedFields)' | \
		kubectl apply -f - -n $(NAMESPACE) 2>&1 | grep -v "Unknown field" || true; \
		echo "   ✅ Copied secret: ai-gateway-azure-openai"; \
	fi
	@echo ""
	@echo "✅ Namespace setup complete!"
	@echo ""

install:
	@echo "Installing KYC Onboarding Bundle..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found."; \
		echo ""; \
		echo "The .env file is required for AI Gateway credentials:"; \
		echo "  - API_TOKEN (required, no default)"; \
		echo "  - AIGW_UUID (required, no default)"; \
		echo ""; \
		echo "To create .env:"; \
		echo "  cp .env.template .env"; \
		echo "  # Edit .env and set API_TOKEN and AIGW_UUID"; \
		echo ""; \
		echo "Optional: You can override NAMESPACE and MCP_SOURCE_NAMESPACE:"; \
		echo "  make install NAMESPACE=my-namespace MCP_SOURCE_NAMESPACE=default"; \
		echo ""; \
		exit 1; \
	fi
	@set -a && . ./.env && set +a && \
	helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--set aigw.token="$$API_TOKEN" \
		--set aigw.uuid="$$AIGW_UUID" \
		--wait
	@echo "Done. Agents and teams are now available."

install-with-argo: setup-namespace
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "📦 Installing KYC Onboarding Bundle"
	@echo "════════════════════════════════════════════════════════════════════"
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found."; \
		echo ""; \
		echo "The .env file is required for AI Gateway credentials:"; \
		echo "  - API_TOKEN (required, no default)"; \
		echo "  - AIGW_UUID (required, no default)"; \
		echo ""; \
		echo "To create .env:"; \
		echo "  cp .env.template .env"; \
		echo "  # Edit .env and set API_TOKEN and AIGW_UUID"; \
		echo ""; \
		echo "Optional: You can override NAMESPACE and MCP_SOURCE_NAMESPACE:"; \
		echo "  make install NAMESPACE=my-namespace MCP_SOURCE_NAMESPACE=default"; \
		echo ""; \
		exit 1; \
	fi
	@set -a && . ./.env && set +a && \
	helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--set aigw.token="$$API_TOKEN" \
		--set aigw.uuid="$$AIGW_UUID" \
		--set argoWorkflows.rbac.enabled=true \
		--timeout 5m
	@echo "Waiting for pods to be ready..."
	@kubectl wait --for=condition=ready pod -l bundle=kyc-onboarding -n $(NAMESPACE) --timeout=120s || echo "Some pods not ready yet, continuing..."
	@echo "Installing WorkflowTemplates..."
	@kubectl apply -f examples/lx-retrieve-ownership-structure-template.yaml -n $(NAMESPACE)
	@kubectl apply -f examples/lx-retrieve-entities-vessels-template.yaml -n $(NAMESPACE)
	@kubectl apply -f examples/lx-retrieve-key-controllers-template.yaml -n $(NAMESPACE)
	@kubectl apply -f examples/lx-assess-purpose-of-relationship-template.yaml -n $(NAMESPACE)
	@kubectl apply -f examples/lx-adverse-media-screening-template.yaml -n $(NAMESPACE)
	@kubectl apply -f examples/lx-blacklist-sanction-screening-template.yaml -n $(NAMESPACE)
	@echo "Done! Installed:"
	@echo "  ✓ Agents and teams"
	@echo "  ✓ Argo Workflows RBAC"
	@echo "  ✓ 6 WorkflowTemplates (visible in ARK Dashboard)"

uninstall:
	@echo "Uninstalling KYC Onboarding Bundle..."
	@helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete rolebinding argo-workflow-default-access -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete workflowtemplate -l bundle=kyc-onboarding -n $(NAMESPACE) 2>/dev/null || true
	@echo "Done."

submit-ownership:
	@echo "Submitting ownership structure workflow..."
	@kubectl create -f examples/lx-retrieve-ownership-structure-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

submit-entities:
	@echo "Submitting entities & vessels workflow..."
	@kubectl create -f examples/lx-retrieve-entities-vessels-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

submit-controllers:
	@echo "Submitting key controllers workflow..."
	@kubectl create -f examples/lx-retrieve-key-controllers-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

submit-purpose:
	@echo "Submitting purpose of relationship workflow..."
	@kubectl create -f examples/lx-assess-purpose-of-relationship-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

submit-media:
	@echo "Submitting adverse media screening workflow..."
	@kubectl create -f examples/lx-adverse-media-screening-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

submit-blacklist:
	@echo "Submitting blacklist & sanction screening workflow..."
	@kubectl create -f examples/lx-blacklist-sanction-screening-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

upload-data:
	@echo "Uploading example customer data and agent guidance files to filesystem-mcp..."
	@echo "Finding filesystem MCP pod..."
	@MCP_POD=$$(kubectl get pods -n $(MCP_SOURCE_NAMESPACE) -l app.kubernetes.io/name=mcp-filesystem -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$MCP_POD" ]; then \
		echo "Error: mcp-filesystem pod not found in namespace $(MCP_SOURCE_NAMESPACE)"; \
		exit 1; \
	fi; \
	echo "Found pod: $$MCP_POD"; \
	echo "Creating directory structure..."; \
	kubectl exec -n $(MCP_SOURCE_NAMESPACE) $$MCP_POD -- mkdir -p \
		/data/source_code_files/1-customer-profile-initialization/input \
		/data/source_code_files/1-customer-profile-initialization/intermediate \
		/data/source_code_files/1-customer-profile-initialization/output \
		/data/source_code_files/2-customer-due-diligence/input \
		/data/source_code_files/2-customer-due-diligence/profile_sections \
		/data/source_code_files/2-customer-due-diligence/output \
		/data/source_code_files/3-kyc-memo/input \
		/data/source_code_files/3-kyc-memo/output; \
	echo "Uploading Phase I input files..."; \
	for file in examples/data/*.txt examples/data/prompts*.yml; do \
		[ -f "$$file" ] || continue; \
		filename=$$(basename "$$file"); \
		echo "  → $$filename (Phase I)"; \
		kubectl cp "$$file" $(MCP_SOURCE_NAMESPACE)/$$MCP_POD:/data/source_code_files/1-customer-profile-initialization/input/$$filename; \
	done; \
	echo "Uploading Phase II input files..."; \
	for file in examples/data/*.yml examples/data/*.json examples/data/*.pdf; do \
		[ -f "$$file" ] || continue; \
		filename=$$(basename "$$file"); \
		echo "  → $$filename (Phase II)"; \
		kubectl cp "$$file" $(MCP_SOURCE_NAMESPACE)/$$MCP_POD:/data/source_code_files/2-customer-due-diligence/input/$$filename; \
	done; \
	echo "Uploading agent guidance files..."; \
	for file in examples/data/*.md; do \
		[ -f "$$file" ] || continue; \
		filename=$$(basename "$$file"); \
		echo "  → $$filename"; \
		kubectl cp "$$file" $(MCP_SOURCE_NAMESPACE)/$$MCP_POD:/data/source_code_files/2-customer-due-diligence/input/$$filename; \
	done; \
	echo "Done. Customer data and agent guidance files uploaded successfully."
