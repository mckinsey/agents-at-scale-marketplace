# KYC Onboarding Demo

Complete KYC (Know Your Customer) workflow implementation migrated from LegacyX to ARK platform. This demo showcases six production-ready workflows covering Phase I-III of customer due diligence.

## Overview

This demo provides end-to-end KYC onboarding workflows that extract, analyze, and screen customer information using a multi-agent architecture with MCP (Model Context Protocol) tool integration.

**Workflows included:**
1. **Ownership Structure Retrieval** - Extract Ultimate Beneficial Owner (UBO) tree from documents
2. **Entities & Vessels Retrieval** - Identify subsidiaries, affiliates, and vessels
3. **Key Controllers Retrieval** - Identify key management and control persons
4. **Purpose of Relationship Assessment** - Analyze business purpose and risk
5. **Adverse Media Screening** - Search for negative news and reputational risks
6. **Blacklist & Sanction Screening** - Check against watchlists and sanctions

**Architecture:**
- **Agents**: Specialized AI agents for document extraction, web research, and analysis
- **Teams**: Multi-agent collaboration (scout-rag-team for two-stage PDF extraction)
- **MCP Servers**: Tool providers for PDF analysis, web research, and file operations
- **Workflows**: Orchestrated Argo Workflows with sequential/parallel execution modes

## Prerequisites

- **Kubernetes cluster** (minikube, kind, or cloud provider)
- **Argo Workflows** 3.4+
- **ARK platform** installed and configured
- **kubectl** configured to access your cluster
- **API Gateway access** (Daily.co or Azure OpenAI)

## Quick Start

### 1. Configure Environment

Create and configure your `.env` file:

```bash
# Copy the template
cp .env.template .env

# Edit with your credentials
vi .env
```

**Multi-provider setup** (choose ARK or LegacyX):
```bash
# ARK Provider
ARK_AIGW_UUID="your-ark-aigw-uuid"
ARK_DAILY_API_TOKEN="your-ark-token"

# LegacyX Provider (optional)
LX_AIGW_UUID="your-legacyx-aigw-uuid"
LX_DAILY_API_TOKEN="your-legacyx-token"

# Select provider by setting:
API_TOKEN=$ARK_DAILY_API_TOKEN
AIGW_UUID=$ARK_AIGW_UUID
```

### 2. Sync Environment to Kubernetes

```bash
cd scripts
./sync-env.sh
```

This will:
- Validate your API_TOKEN and AIGW_UUID
- Update the `aigw-secret` in Kubernetes
- Restart MCP server deployments
- Show which provider is active (ARK or LegacyX)

### 3. Deploy MCP Servers

```bash
# Deploy filesystem MCP server
kubectl apply -f mcp-servers/mcp-filesystem-deployment.yaml

# Deploy PDF tools MCP server
kubectl apply -f mcp-servers/ubo-pdf-tools/

# Deploy web tools MCP server
kubectl apply -f mcp-servers/ubo-web-tools/

# Verify deployments
kubectl get deployments | grep mcp
```

### 4. Deploy Agents

```bash
kubectl apply -f agents/
kubectl get agents
```

Expected agents:
- `scout-agent` - Scans PDFs to locate relevant sections
- `rag-agent` - Extracts structured data from documents
- `profile-web-enricher` - Performs web research and enrichment
- `companies-house-enricher` - Enriches UK company data

### 5. Deploy Teams

```bash
kubectl apply -f teams/
kubectl get teams
```

The `scout-rag-team` provides two-stage PDF extraction:
1. Scout agent scans entire document
2. RAG agent performs targeted extraction

### 6. Deploy Workflows

```bash
kubectl apply -f argo-workflows/
argo template list
```

You should see 6 workflows prefixed with `lx-`:
- `lx-retrieve-ownership-structure-workflow`
- `lx-retrieve-entities-vessels-workflow`
- `lx-retrieve-key-controllers-workflow`
- `lx-assess-purpose-of-relationship-workflow`
- `lx-adverse-media-screening-workflow`
- `lx-blacklist-sanction-screening-workflow`

### 7. Run a Workflow

```bash
cd scripts
./run-workflow.sh ownership seq
```

**Execution modes:**
- `seq` / `sequential` - Steps run one after another
- `par` / `parallel` - Independent steps run concurrently
- `fake` - Simulates execution without real API calls

**Workflow short names:**
- `ownership` / `os` → Retrieve ownership structure
- `vessels` / `ev` → Retrieve entities and vessels
- `controllers` / `kc` → Retrieve key controllers
- `purpose` / `pr` → Assess purpose of relationship
- `media` / `am` → Adverse media screening
- `blacklist` / `bs` → Blacklist screening

**Monitor workflow:**
```bash
# Watch workflow progress
argo watch <workflow-name>

# View workflow logs
argo logs <workflow-name>

# Get workflow status
argo get <workflow-name>
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Argo Workflows                        │
│  (Orchestration: lx-retrieve-ownership-structure, etc.)  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │  Agents  │          │  Teams   │
    │          │          │          │
    │ • scout  │          │ scout-   │
    │ • rag    │◄─────────┤ rag-team │
    │ • web    │          │          │
    │ • enricher│         └──────────┘
    └────┬─────┘
         │
    ┌────▼──────────────────────────┐
    │       MCP Servers             │
    │                               │
    │ • ubo-pdf-tools               │
    │   - analyze_pdf_ownership     │
    │   - scout_pdf_for_ownership   │
    │                               │
    │ • ubo-web-tools               │
    │   - research_ubo_web          │
    │   - perplexity_search         │
    │                               │
    │ • mcp-filesystem              │
    │   - read-file, write-file     │
    │   - list-directory            │
    └───────────────────────────────┘
```

### Workflow Patterns

**Declarative Queries** (Tell WHAT, not HOW):
```yaml
# ✅ CORRECT - Declarative
spec:
  input: |
    Extract ownership information from: {{.document_file}}
    Save results to: /mnt/output/{{.output_file}}
  target:
    type: team
    name: scout-rag-team

# ❌ WRONG - Imperative (don't specify tools)
spec:
  input: "Use analyze_pdf_ownership tool to extract..."
```

**Two-Stage Extraction** (scout-rag-team):
1. **Scout phase**: Agent scans entire PDF, identifies relevant pages
2. **RAG phase**: Agent performs targeted extraction from identified sections
3. **Result**: More accurate extraction with better context

## Data Files

Sample data files are provided in `data/`:

**Input Files:**
- `kyc_profile.json` - Customer profile with basic information
- `prompts_ownership_structure.yml` - Extraction prompts for ownership data
- `prompts_entities_vessels.yml` - Extraction prompts for entities
- `prompts_key_controllers.yml` - Extraction prompts for controllers
- `prompts_adverse_media_screening.yml` - Screening queries
- `mock-up-blacklist.json` - Sample blacklist for testing
- `abf-annual-report-2024.pdf` - Test document for extraction

**File Locations in Workflows:**
- Input files: `/mnt/output/source_code_files/2-customer-due-diligence/input/`
- Output files: `/mnt/output/source_code_files/2-customer-due-diligence/output/`

## Workflows

### 1. Retrieve Ownership Structure

**Purpose**: Extract Ultimate Beneficial Owner (UBO) tree from corporate documents

**Template**: `lx-retrieve-ownership-structure-workflow`

**Steps**:
1. Read prompts file (ownership structure extraction rules)
2. Document extraction (two-stage: scout → RAG)
3. Determine direct beneficial owners
4. Determine indirect beneficial owners
5. Create beneficial owner tree (JSON structure)
6. Draw ownership diagram

**Output**: JSON file with complete ownership hierarchy and visual diagram

**Example**:
```bash
./scripts/run-workflow.sh ownership seq
```

### 2. Retrieve Entities & Vessels

**Purpose**: Identify subsidiaries, affiliates, and vessels owned by customer

**Template**: `lx-retrieve-entities-vessels-workflow`

**Steps**:
1. Read prompts file (entity extraction rules)
2. Document extraction (scout-rag-team)
3. Consolidate entities list
4. Enrich with web data

**Output**: JSON file with entities, vessels, and ownership percentages

### 3. Retrieve Key Controllers

**Purpose**: Identify key management and control persons

**Template**: `lx-retrieve-key-controllers-workflow`

**Steps**:
1. Read prompts file (controller identification rules)
2. Document extraction (scout-rag-team)
3. Web research for additional information
4. Consolidate results

**Output**: JSON file with key controllers and their roles

### 4. Assess Purpose of Relationship

**Purpose**: Analyze business purpose and relationship risk

**Template**: `lx-assess-purpose-of-relationship-workflow`

**Steps**:
1. Analyze customer profile
2. Research business activities
3. Assess risk factors
4. Generate risk report

**Output**: Risk assessment report with recommendations

### 5. Adverse Media Screening

**Purpose**: Search for negative news and reputational risks

**Template**: `lx-adverse-media-screening-workflow`

**Steps**:
1. Read screening queries
2. Execute web searches (Perplexity)
3. Analyze results
4. Generate screening report

**Output**: Adverse media findings with sources

### 6. Blacklist & Sanction Screening

**Purpose**: Check customer against watchlists and sanctions

**Template**: `lx-blacklist-sanction-screening-workflow`

**Steps**:
1. Load blacklist data
2. Match customer against lists
3. Check sanctions databases
4. Generate compliance report

**Output**: Compliance screening results with matches

## Troubleshooting

### 403 Forbidden Errors

**Symptom**: Queries return `403 Forbidden` from API Gateway

**Cause**: Invalid or expired API token

**Solution**:
```bash
# 1. Check your token is set correctly
echo $API_TOKEN

# 2. Verify it matches your provider
source .env
echo $API_TOKEN

# 3. Re-sync environment
cd scripts
./sync-env.sh

# 4. Restart MCP servers
kubectl rollout restart deployment mcp-filesystem
kubectl rollout restart deployment ubo-pdf-tools
kubectl rollout restart deployment ubo-web-tools
```

### Workflow Steps Skipped

**Symptom**: Steps show as "Skipped" in workflow

**Cause**: 
- `withParam` received empty array (no items to iterate)
- Condition not met (`when` clause evaluated to false)
- Previous step returned no results

**Solution**:
```bash
# 1. Check previous step output
argo logs <workflow-name> <step-name>

# 2. Verify execution mode
./run-workflow.sh ownership seq  # Use 'seq' not 'sequential'

# 3. Check if fake mode
argo get <workflow-name> -o yaml | grep execution-mode
```

### MCP Server Not Available

**Symptom**: Agent cannot find MCP tool

**Cause**: MCP server deployment not running or not configured

**Solution**:
```bash
# 1. Check MCP server status
kubectl get deployments | grep mcp
kubectl get pods | grep mcp

# 2. Check agent configuration
kubectl get agent <agent-name> -o yaml | grep -A 10 tools

# 3. Restart MCP servers
kubectl rollout restart deployment/<mcp-server-name>

# 4. Check logs
kubectl logs deployment/<mcp-server-name>
```

### Empty Extraction Results

**Symptom**: Document extraction returns no data

**Cause**:
- Document format not recognized
- Prompts don't match document content
- Scout agent didn't find relevant sections

**Solution**:
```bash
# 1. Test with scout-rag-team
kubectl exec -it deployment/mcp-filesystem -- cat /mnt/output/scout_results.json

# 2. Check document format
file data/abf-annual-report-2024.pdf

# 3. Manually test scout
# Create test query targeting scout-agent

# 4. Review prompts
cat data/prompts_ownership_structure.yml
```

### Environment Variable Issues

**Symptom**: `source .env` fails or variables not set

**Cause**: Syntax error in .env file

**Solution**:
```bash
# 1. Check for syntax errors
bash -n .env  # Should return no output if valid

# 2. Look for common issues
grep -n '=' .env | grep -v '^#'  # Check for proper quotes

# 3. Validate required variables
source .env
echo "API_TOKEN: ${API_TOKEN:0:20}..."
echo "AIGW_UUID: ${AIGW_UUID}"
```

### Prompts File Format Error

**Symptom**: Workflow fails with "withParam expected array, got object"

**Cause**: YAML prompts file has nested structure instead of array

**Solution**: Use updated workflow templates (already fixed in this demo)

The `read-prompts-file` template transforms prompts automatically:
```yaml
# Transforms this (object):
ownership_structure:
  direct_owners:
    objective: "Extract direct owners..."

# Into this (array):
[
  {
    "section": "direct_owners",
    "prompt": "Extract direct owners..."
  }
]
```

## Advanced Usage

### Switching Providers

Edit `.env` to switch between ARK and LegacyX:

```bash
# Use ARK
API_TOKEN=$ARK_DAILY_API_TOKEN
AIGW_UUID=$ARK_AIGW_UUID

# Or use LegacyX
API_TOKEN=$LX_DAILY_API_TOKEN
AIGW_UUID=$LX_AIGW_UUID

# Then sync
./scripts/sync-env.sh
```

### Custom Prompts

Modify prompt files in `data/` to customize extraction:

```yaml
# prompts_ownership_structure.yml
ownership_structure:
  direct_owners:
    objective: |
      Extract information about direct beneficial owners.
      Include: name, ownership percentage, type of control.
  
  indirect_owners:
    objective: |
      Identify indirect beneficial owners through subsidiaries.
```

### Parallel Execution

For faster processing, use parallel mode:

```bash
./scripts/run-workflow.sh ownership par
```

**Note**: Only independent steps run in parallel. Sequential dependencies are preserved.

### Custom Execution Mode

Override execution mode in workflow parameters:

```bash
argo submit argo-workflows/lx-retrieve-ownership-structure-workflow.yaml \
  --parameter execution-mode=fake \
  --parameter document_file=/mnt/output/source_code_files/2-customer-due-diligence/input/abf-annual-report-2024.pdf
```

## Further Documentation

- **CLAUDE.md** - Complete migration guide with best practices
- **ARK Documentation** - https://ark.mckinsey.com/docs
- **Argo Workflows** - https://argoproj.github.io/workflows

## Support

For issues or questions:
1. Check Troubleshooting section above
2. Review CLAUDE.md for detailed guidance
3. Check workflow logs: `argo logs <workflow-name>`
4. Inspect agent status: `kubectl get agents`

## License

© 2024 McKinsey & Company. Internal use only.
