# KYC Onboarding Bundle

End-to-end KYC (Know Your Customer) onboarding workflows for customer due diligence, with multi-agent document extraction, web research, and compliance screening.

## What's Included

**21 agents** organized into **6 teams** covering Phase I–III of customer due diligence:

| Ark Agent | Description |
|-----------|-------------|
| `scout-agent` | Scans PDFs to locate relevant sections |
| `rag-agent` | Extracts structured data from documents |
| `doc-planner-agent` | Plans document extraction strategy |
| `doc-analyst-agent` | Analyzes document content |
| `web-planner-agent` | Plans web research tasks |
| `web-analyst-agent` | Analyzes web research results |
| `web-researcher-agent` | Performs web research via Tavily or Perplexity |
| `ch-planner-agent` | Plans Companies House lookups |
| `ch-analyst-agent` | Analyzes Companies House data |
| `ch-api-agent` | Queries Companies House API |
| `consolidation-planner-agent` | Plans data consolidation |
| `consolidation-analyst-agent` | Consolidates extracted data |
| `beneficial-owner-tree-agent` | Builds ownership tree structures |
| `relevance-classification-agent` | Classifies content relevance |
| `file-manager-agent` | Manages file read/write operations |
| `critic-agent` | Reviews and validates outputs |
| `summary-assessment-agent` | Generates summary assessments |
| `bo-planner` | Plans beneficial ownership research missions |
| `companies-house-expert` | UK Companies House API expert for ownership data |
| `bo-web-researcher` | Web research for beneficial ownership information |
| `bo-analyst` | Structures ownership data into tree format |

**Teams:**
- `scout-rag-team` — Two-stage PDF extraction (scout → RAG)
- `doc-extraction-team` — Document analysis and extraction
- `web-research-team` — Web research coordination
- `companies-house-team` — Companies House data enrichment
- `consolidation-team` — Data consolidation across sources
- `beneficial-owners-team` — Beneficial ownership analysis

**12 Argo WorkflowTemplates:**
- **Phase I** — `lx-profile-initialization`, `lx-profile-enrichment`, `lx-requirements-and-standards`, `lx-initial-risk-assessment`
- **Phase II** — `lx-retrieve-ownership-structure`, `lx-retrieve-entities-vessels`, `lx-retrieve-key-controllers`, `lx-adverse-media-screening`, `lx-blacklist-sanction-screening`, `lx-assess-purpose-of-relationship`
- **Profile finalization** — `lx-profile-finalization`
- **Phase III** — `lx-kyc-memo`

**Supporting infrastructure:** File Gateway (Helm dependency), PDF extraction MCP, web research MCP, Perplexity Ask MCP, Companies House MCP, data seeder job, RBAC.

## Prerequisites

- Ark cluster with Argo Workflows 3.4+
- A Model named `default` in the target namespace (create via Ark Dashboard → Models)
- `kubectl` and `helm` CLI tools

## Secrets Setup

Create these secrets in the bundle namespace before deploying MCPs:

```bash
# 1. Azure OpenAI credentials (for pdf-extraction MCP)
kubectl create secret generic ai-gateway-azure-openai -n default \
  --from-literal=base-url='https://YOUR_AZURE_OPENAI_ENDPOINT/' \
  --from-literal=token='YOUR_AZURE_OPENAI_API_KEY'

# 2. Web search credentials (for web-research MCP — at least one key required)
kubectl create secret generic web-search-credentials -n default \
  --from-literal=tavily-api-key='YOUR_TAVILY_API_KEY' \
  --from-literal=perplexity-api-key='YOUR_PERPLEXITY_API_KEY'

# 3. Companies House API key (for companies-house MCP — required)
#    Register for a free key at https://developer.company-information.service.gov.uk/get-started
kubectl create secret generic companies-house-api-key -n default \
  --from-literal=api-key='YOUR_COMPANIES_HOUSE_API_KEY'
```

## Quick Start

```bash
cd demos/kyc-onboarding-bundle
make uninstall                    # Clean any previous install
```

### Option A: Data seeder (automatic upload on install)

Build the data-seeder image first — the post-install hook uploads sample data automatically.

```bash
make build-data-seeder
make install-with-argo
make build
make ready
```

### Option B: Manual upload

Install with the data seeder disabled, then upload sample data manually.

```bash
make install-with-argo DATA_SEEDER_ENABLED=false
make build
make upload-data
make ready
```

After `make ready`, wait 30–60s and refresh Ark Dashboard for agents/teams to show Available.

### Troubleshooting: "File Gateway Service Not Configured"

If the Ark Dashboard **Files** page shows **"File Gateway Service Not Configured"** instead of an empty file list, the File Gateway needs to be set up first before seeding data:

1. Follow the [File Gateway Service](https://github.com/mckinsey/agents-at-scale-marketplace/tree/main/services/file-gateway) setup instructions in the Ark Dashboard
2. Build and run the data seeder:
   ```bash
   make build-data-seeder
   make install-with-argo
   ```
3. Verify files appear in **Ark Dashboard > Files**

This typically happens on a fresh Ark cluster where the File Gateway has not been configured previously. Once the File Gateway service is registered with the dashboard, subsequent installs will work with either Option A or Option B above.

## Running Workflows

```bash
# Phase I
make submit-profile-init          # Extract inquiry info
make submit-profile-enrichment    # Enrich with web + Companies House data
make submit-requirements          # Retrieve KYC requirements
make submit-initial-risk          # Produce KYC profile + risk report

# Phase II
make submit-ownership             # Ownership structure + UBO tree
make submit-entities              # Subsidiaries, affiliates, vessels
make submit-controllers           # Key management persons
make submit-media                 # Adverse media screening
make submit-blacklist             # Watchlist/sanction screening
make submit-purpose               # Business purpose analysis

# Profile finalization + Phase III
make submit-profile-finalization  # Merge into final profile
make submit-kyc-memo              # Generate KYC memo
```

Use `NAMESPACE=<ns>` for a non-default namespace.

## Validation — Expected Output Files

After each workflow completes, verify the output files in **Ark Dashboard → Files** under `source_code_files/`.

### Phase I — Customer Profile Initialization

| Workflow | Make Target | Output Files (under `1-customer-profile-initialization/`) |
|----------|-------------|-----------------------------------------------------------|
| Profile Initialization | `make submit-profile-init` | `intermediate/inquiry_information.json` |
| Requirements & Standards | `make submit-requirements` | `intermediate/kyc_standards.json` |
| Profile Enrichment | `make submit-profile-enrichment` | `intermediate/web_data_initial_profile.json`, `intermediate/government_data_initial_profile.json` |
| Initial Risk Assessment | `make submit-initial-risk` | `output/kyc_profile.json`, `output/kyc_profile.md`, `output/summary_risk_report.md` |

### Phase II — Customer Due Diligence

| Workflow | Make Target | Output Files (under `2-customer-due-diligence/`) |
|----------|-------------|---------------------------------------------------|
| Ownership Structure | `make submit-ownership` | `profile_sections/ownership_structure.json`, `profile_sections/beneficial_ownership_tree.json`, `output/beneficial_ownership_tree.puml` |
| Entities & Vessels | `make submit-entities` | `profile_sections/entities_vessels.json` |
| Key Controllers | `make submit-controllers` | `profile_sections/key_controllers.json` |
| Adverse Media Screening | `make submit-media` | `profile_sections/adverse_media_screening.json`, `output/adverse_media_screening_summary.md` |
| Blacklist/Sanction Screening | `make submit-blacklist` | `profile_sections/sanction_blacklist_screening.json`, `output/sanction_blacklist_screening_report.md` |
| Purpose of Relationship | `make submit-purpose` | `profile_sections/purpose_of_relationship.json` |

### Profile Finalization & Phase III

| Workflow | Make Target | Output Files |
|----------|-------------|--------------|
| Profile Finalization | `make submit-profile-finalization` | `2-customer-due-diligence/output/kyc_profile.json`, `2-customer-due-diligence/output/kyc_profile.md` |
| KYC Memo | `make submit-kyc-memo` | `3-kyc-memo/output/kyc_memo.md` |

> **Tip:** To check workflow status, run: `kubectl get workflows -n default -w`. To inspect a failed Query: `kubectl get query -n default --sort-by=.metadata.creationTimestamp -o name | tail -1 | xargs kubectl get -n default -o yaml`.

## Useful Make Targets

| Target | Description |
|--------|-------------|
| `make install-with-argo` | Deploy bundle with WorkflowTemplates |
| `make build` | Build and deploy all MCP images |
| `make build-companies-house-mcp` | Deploy Companies House MCP only |
| `make upload-data` | Upload sample data to file-gateway |
| `make ready` | Full deployment readiness check |
| `make verify-mcp` | Verify MCP servers and Tool CRs |
| `make verify-agents` | List all agents (expects 21) |
| `make upgrade` | Helm upgrade (auto-detects existing file-gateway) |
| `make uninstall` | Remove bundle |
| `make clean` | Cleanup resources |

## Cloud Deployment

```bash
ark install marketplace/demos/kyc-onboarding-bundle
```

Upload KYC documents via **Ark Dashboard → Files** to `source_code_files/`, then submit workflows from **Ark Dashboard → Argo Workflows** or apply example manifests from [`examples/`](examples/).
