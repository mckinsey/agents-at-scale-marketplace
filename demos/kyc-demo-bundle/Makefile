.PHONY: help install install-with-argo uninstall demo

NAMESPACE ?= default
RELEASE_NAME ?= kyc-demo-bundle

help:
	@echo "KYC Demo Bundle"
	@echo ""
	@echo "Available commands:"
	@echo "  make install              Install bundle (agents + teams + file-gateway)"
	@echo "  make install-with-argo    Install bundle with Argo Workflows RBAC"
	@echo "  make uninstall            Remove bundle and cleanup"
	@echo "  make demo                 Submit example workflow"
	@echo "  make upload-data          Upload example customer data to file-gateway"

install:
	@echo "Installing KYC Demo Bundle..."
	@echo "Building Helm dependencies..."
	@helm dependency build chart/
	@helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait
	@echo "Done. Agents, teams, and file-gateway are now available."

install-with-argo:
	@echo "Installing KYC Demo Bundle with Argo support..."
	@echo "Building Helm dependencies..."
	@helm dependency build chart/
	@helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--set argoWorkflows.rbac.enabled=true \
		--wait
	@echo "Done. Argo Workflows RBAC configured."

uninstall:
	@echo "Uninstalling KYC Demo Bundle..."
	@helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete rolebinding argo-workflow-default-access -n $(NAMESPACE) 2>/dev/null || true
	@echo "Done."

demo:
	@echo "Submitting KYC workflow..."
	@kubectl create -f examples/kyc-onboarding-workflow.yaml
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE)"

upload-data:
	@echo "Uploading example customer data to file-gateway..."
	@echo "Creating directory structure..."
	@kubectl exec -n $(NAMESPACE) deployment/file-gateway-filesystem-mcp -- mkdir -p /data/aas-files/customers /data/aas-files/reports
	@echo "Starting port-forward to file-gateway API..."
	@(kubectl port-forward -n $(NAMESPACE) svc/file-gateway-api 8181:80 > /dev/null 2>&1 &) && \
	sleep 4 && \
	echo "Testing connection..." && \
	curl -s http://localhost:8181/health > /dev/null && \
	echo "Uploading customers/john-doe.txt..." && \
	curl -X POST http://localhost:8181/files \
		-F "file=@examples/data/customers/john-doe.txt" \
		-F "prefix=customers/" && \
	echo "" && \
	pkill -f "port-forward.*file-gateway-api" > /dev/null 2>&1 && \
	echo "Done. Customer data uploaded successfully."
