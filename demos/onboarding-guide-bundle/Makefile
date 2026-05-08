.PHONY: help build install install-with-argo uninstall onboarding-demo fetch-output clean

NAMESPACE ?= default
RELEASE_NAME ?= onboarding-guide-bundle
CHART_DIR ?= chart
# Set to true to skip installing file-gateway and use the one already in the namespace.
USE_EXISTING_FILE_GATEWAY ?= false
# Set to 1 to skip `helm dependency build` (run once manually first if it hangs).
SKIP_DEP_BUILD ?= 0

FILE_GATEWAY_SKIP_FLAGS := \
	--set file-gateway.enabled=false \
	--set file-gateway.fileApi.enabled=false \
	--set file-gateway.filesystemMcp.enabled=false \
	--set file-gateway.versitygw.enabled=false \
	--set file-gateway.versitygw.createSecret=false \
	--set file-gateway.storage.enabled=false \
	--set file-gateway.httpRoute.enabled=false

ifeq ($(USE_EXISTING_FILE_GATEWAY),true)
FILE_GATEWAY_SKIP := $(FILE_GATEWAY_SKIP_FLAGS)
else
FILE_GATEWAY_SKIP :=
endif

help:
	@echo "Onboarding Guide Demo Bundle"
	@echo ""
	@echo "Namespace: $(NAMESPACE) (override with NAMESPACE=my-ns)"
	@echo ""
	@echo "Required steps (prerequisites: 'default' and 'responses' Models must exist in"
	@echo "the target namespace, and Claude Agent SDK + OpenAI Responses executors must"
	@echo "be installed via 'ark install marketplace/executors/...'):"
	@echo ""
	@echo "  export ANTHROPIC_API_KEY=..."
	@echo "  make uninstall             Remove bundle (and file-gateway, unless shared)"
	@echo "  make build                 helm dependency build"
	@echo "  make install-with-argo     Install bundle + file-gateway + WorkflowTemplate"
	@echo "  make onboarding-demo REPO_URL=https://github.com/<owner>/<repo>"
	@echo "                             Run the onboarding-generate workflow"
	@echo "  make fetch-output WF=<workflow-name>"
	@echo "                             Download analysis.md / ONBOARDING.md / TICKET.md"
	@echo ""
	@echo "Options:"
	@echo "  USE_EXISTING_FILE_GATEWAY=true   reuse an existing file-gateway in the namespace"
	@echo "  SKIP_DEP_BUILD=1                skip 'helm dependency build' (pre-built charts)"

build:
ifneq ($(SKIP_DEP_BUILD),1)
	helm dependency build $(CHART_DIR)
else
	@echo "skipping helm dependency build (SKIP_DEP_BUILD=1)"
endif

install: build
	@test -n "$$ANTHROPIC_API_KEY" || (echo "ERROR: export ANTHROPIC_API_KEY=... before installing"; exit 1)
	helm upgrade --install $(RELEASE_NAME) $(CHART_DIR) \
		--namespace $(NAMESPACE) --create-namespace \
		--set anthropic.apiKey="$$ANTHROPIC_API_KEY" \
		$(FILE_GATEWAY_SKIP)

install-with-argo: install
	@echo "Bundle installed. The WorkflowTemplate 'onboarding-generate' is ready."
	@echo "Kick off a run with: make onboarding-demo REPO_URL=https://github.com/<owner>/<repo>"

uninstall:
	-helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE)

onboarding-demo:
	@test -n "$(REPO_URL)" || (echo "ERROR: pass REPO_URL=https://github.com/<owner>/<repo>"; exit 1)
	kubectl -n $(NAMESPACE) create -f - <<EOF
	apiVersion: argoproj.io/v1alpha1
	kind: Workflow
	metadata:
	  generateName: onboarding-
	spec:
	  workflowTemplateRef:
	    name: onboarding-generate
	  arguments:
	    parameters:
	      - name: repo-url
	        value: $(REPO_URL)
	EOF

fetch-output:
	@test -n "$(WF)" || (echo "ERROR: pass WF=<workflow-name> (e.g. WF=onboarding-xyz)"; exit 1)
	./scripts/fetch-output.sh $(WF) $(NAMESPACE)

clean: uninstall
