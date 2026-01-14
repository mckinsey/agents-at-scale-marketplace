.PHONY: help install install-with-argo uninstall demo

NAMESPACE ?= default
RELEASE_NAME ?= kyc-demo-bundle

help:
	@echo "KYC Demo Bundle"
	@echo ""
	@echo "Available commands:"
	@echo "  make install              Install bundle (agents + teams)"
	@echo "  make install-with-argo    Install bundle with Argo Workflows RBAC"
	@echo "  make uninstall            Remove bundle and cleanup"
	@echo "  make demo                 Submit example workflow"

install:
	@echo "Installing KYC Demo Bundle..."
	@helm upgrade --install $(RELEASE_NAME) chart/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait
	@echo "Done. Agents and teams are now available."

install-with-argo:
	@echo "Installing KYC Demo Bundle with Argo support..."
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
