.PHONY: help install install-with-argo uninstall kyc-demo upload-data

NAMESPACE ?= kyc-demo
RELEASE_NAME ?= kyc-demo-bundle

help:
	@echo "KYC Demo Bundle"
	@echo ""
	@echo "Available commands:"
	@echo "  make install-with-argo    Install everything (bundle + WorkflowTemplate)"
	@echo "  make upload-data          Upload example customer data"
	@echo "  make kyc-demo             Run KYC workflow"
	@echo "  make uninstall            Remove bundle and cleanup"

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
	@echo "Installing WorkflowTemplate..."
	@kubectl apply -f examples/kyc-onboarding-template.yaml -n $(NAMESPACE)
	@echo "Done! Installed:"
	@echo "  ✓ Agents, teams, and file-gateway"
	@echo "  ✓ Argo Workflows RBAC"
	@echo "  ✓ WorkflowTemplate (visible in ARK Dashboard)"

uninstall:
	@echo "Uninstalling KYC Demo Bundle..."
	@helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete rolebinding argo-workflow-default-access -n $(NAMESPACE) 2>/dev/null || true
	@echo "Done."

kyc-demo:
	@echo "Submitting KYC workflow from template..."
	@kubectl create -f examples/kyc-onboarding-from-template.yaml -n $(NAMESPACE)
	@echo "Done. Monitor with: kubectl get workflows -n $(NAMESPACE) -w"

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
