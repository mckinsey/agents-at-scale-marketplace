# CLAUDE.md - LegacyX to ARK Migration Expert

## Mission
You are an expert in migrating KYC workflows from the **LegacyX platform** to **ARK (Agents at Scale)** platform. This document contains the complete migration strategy, mappings, conventions, and best practices learned from migrating the `kyc-onboarding/3.45.0` demo.

---

## Naming Conventions

### Argo Workflow Files
**IMPORTANT**: All Argo Workflow YAML files migrated from LegacyX must be prefixed with `lx-` to distinguish them from native ARK workflows.

- **Convention**: `lx-{workflow-name}-workflow.yaml`
- **Example**: `lx-retrieve-entities-vessels-workflow.yaml`
- **Location**: `/argo-workflows/lx-*.yaml`

This prefix helps:
- Identify which workflows are LegacyX migrations
- Separate migrated workflows from native ARK workflows
- Track migration progress

---

## File Access Patterns

### Current Limitation: ARK Query Pods and File Access

**Problem**: ARK Query pods (where agents run) do **NOT** have access to minikube mounts or hostPath volumes.

**What works:**
- ✅ `mcp-filesystem` pod CAN access `/mnt/output` (has hostPath volume)
- ✅ `mcp-filesystem-*` tools work (they call the mcp-filesystem service)
- ✅ Agents can use `mcp-filesystem-read-file` and `mcp-filesystem-write-file` to access files

**What doesn't work:**
- ❌ `analyze_pdf_ownership` tool trying to read files directly from filesystem
- ❌ ARK Query pods cannot access `/mnt/output/data/pdfs/` even if file exists
- ❌ Any tool that opens files directly (not via mcp-filesystem service)

### Solutions

**Development (current - UNSTABLE):**
1. **minikube mount** (frequently dies, not recommended):
   ```bash
   minikube mount /Users/Antonio_Attanasio/ark/ubo-resolver/output:/mnt/output &
   # Process dies randomly, requiring frequent restarts
   # Both mcp-filesystem and ubo-pdf-tools need pod restarts after mount restarts
   ```
2. Files must be copied to `/mnt/output/source_code_files/` for mcp-filesystem access
3. **CRITICAL**: Both `ubo-pdf-tools` and `mcp-filesystem` have `/mnt/output` mounted
   - After minikube mount restarts, BOTH pods must be restarted:
   ```bash
   kubectl delete pod -l app=ubo-pdf-tools
   kubectl delete pod -l app.kubernetes.io/name=filesystem-mcp
   ```

**Production (STRONGLY RECOMMENDED):**
1. **Use HTTPS URLs for PDFs** (RECOMMENDED - implemented in workflows): 
   - Start local HTTP server: `python3 -m http.server 8000` in PDFs directory
   - Pass URL to workflow: `http://host.docker.internal:8000/file.pdf`
   - `analyze_pdf_ownership` tool supports direct URL access
   - No mount instability issues
   - Works with ARK Query pods out of the box
   - Configured via `file-access-mode` parameter (http/mount)
2. **Embed in container images**: Build static PDFs into Docker images (for unchanging datasets)
3. **PersistentVolumes with NFS/EFS**: Use Kubernetes PVs with ReadWriteMany access mode

### Agent Instructions for File Operations

Both `rag-agent` and `profile-web-enricher` now include explicit instructions:

```yaml
When asked to read or write files:
- To read a file: Use the 'mcp-filesystem-read-file' tool
- To write a file: Use the 'mcp-filesystem-write-file' tool
- To list directory: Use the 'mcp-filesystem-list-directory' tool
```

**Workflow queries must explicitly mention which tool to use:**
```
INSTRUCTIONS:
1. Use the 'analyze_pdf_ownership' tool to search the document
2. After extraction, save the results as JSON using the 'mcp-filesystem-write-file' tool
3. Save to this exact path: $OUTPUT_FILE
```

## Platform Differences Overview

### Core Architectural Differences

| Aspect | LegacyX | ARK |
|--------|---------|-----|
| **Team Definition** | Squads (agents defined inside) | Teams (references to separate Agent CRDs) |
| **Agent Definition** | Nested inside Squad YAML | Independent Agent CRDs with own schema |
| **Groups** | Groups with embedded goals/prompts | Simplified to single agents or 2-agent teams |
| **Goals/Prompts** | Embedded in group definitions | Passed as Query input at execution time |
| **Workflows** | LegacyX Flow YAML | Argo WorkflowTemplate |
| **Iteration** | Built-in `iterate_on` with kwargs passing | Explicit loops (sequential) or `withParam` (parallel) |
| **File Access** | Direct filesystem access in transformers | Via MCP tools (file-gateway-mcpserver) |
| **Context Passing** | Session-based kwargs auto-passing | Explicit via workflow parameters and file operations |
| **Tools** | Embedded in transformer bundles | MCP Server CRDs with Tool discovery |

---

## Environment Configuration

### Multi-Provider Setup

The `.env` file supports multiple API Gateway providers (ARK and LegacyX), allowing you to switch between workspaces easily:

```bash
# Two providers defined with their own credentials
LX_AIGW_UUID="0dbd4a38-****-****-****-************"
LX_DAILY_API_TOKEN="eyJhbGciOiJS..."

ARK_AIGW_UUID="f4b31f5f-****-****-****-************"
ARK_DAILY_API_TOKEN="eyJhbGciOiJS..."

# Generic variables that point to selected provider
API_TOKEN=$ARK_DAILY_API_TOKEN
AIGW_UUID=$ARK_AIGW_UUID

# All service configurations use generic variables
OPENAI_API_KEY=${API_TOKEN}
OPENAI_BASE_URL="https://openai.us.prod.ai-gateway.quantumblack.com/${AIGW_UUID}/v1"

ANTHROPIC_API_KEY=${API_TOKEN}
ANTHROPIC_BASE_URL="https://anthropic.us.prod.ai-gateway.quantumblack.com/${AIGW_UUID}"
```

**Switching Providers:**
- Change `API_TOKEN=$LX_DAILY_API_TOKEN` to switch to LegacyX
- Change `AIGW_UUID=$LX_AIGW_UUID` to use LegacyX workspace
- Run `./scripts/sync-env.sh` to apply changes to Kubernetes

**sync-env.sh validates:**
- `API_TOKEN` is set (not the old `DAILY_API_TOKEN`)
- `AIGW_UUID` is set
- Shows which provider is active (ARK or LegacyX)

---

## Entity Type Mappings

### 1. Squads → Teams

**LegacyX Squad:**
```yaml
squad:
  name: my-squad
  agents:
    - name: worker-agent
      role: main
      model: gpt-4
    - name: critic-agent
      role: critic
      model: gpt-4
```

**ARK Team:**
```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Team
metadata:
  name: my-team
spec:
  description: |
    Team description here
  strategy: graph  # or sequential, parallel
  maxTurns: 3
  members:
    - name: worker-agent  # References existing Agent CRD
      type: agent
    - name: critic-agent
      type: agent
  graph:
    edges:
      - from: worker-agent
        to: critic-agent
      - from: critic-agent
        to: worker-agent
```

**Key Differences:**
- Agents must exist as separate CRDs before team creation
- No `role` field - relationships defined via `graph.edges`
- No inline agent configuration
- `maxIterations` → `maxTurns`

### 2. Groups → Agents or Teams

**Migration Strategy:**
1. **Simple Groups (single goal)** → Single Agent with Query input
2. **Groups with Critic** → 2-Agent Team (worker + critic, graph strategy)
3. **Complex Groups** → Multi-agent Team with orchestration

**Decision Tree:**
```
Group has critic? 
  YES → Create 2-agent team (main + critic, graph strategy, maxTurns: 3)
  NO → Use single agent with Query input
```

**Example Migration:**

LegacyX Group:
```yaml
group:
  name: information_from_document
  goal: "Extract information from document"
  agents:
    - document-analyzer
```

ARK Query to Existing Agent:
```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: extract-info-query
spec:
  input: |
    Extract information from document: {document_path}
    
    Focus: {specific_prompt}
    
    Save results to: {output_file}
  target:
    type: agent
    name: rag-agent  # Existing ARK agent
  timeout: 5m
```

### 3. Transformers → Script Templates or Agent Queries

**Category A: Deterministic Transformers** → Alpine/Shell Script Templates
- Date operations (`get_current_date`)
- JSON manipulation (`combine_json` with `jq`)
- File operations (`readdir`)
- String operations

**Category B: AI-Required Transformers** → ARK Query to Agent
- YAML parsing requiring interpretation (`yaml_to_list`)
- Content extraction requiring understanding
- Data transformation requiring reasoning

**Implementation Pattern:**

Deterministic (Shell Script):
```yaml
- name: get-current-date-script
  script:
    image: alpine:3.19
    command: [sh]
    source: |
      date +"%Y-%m-%d"
```

AI-Required (Agent Query):
```yaml
- name: parse-yaml-via-agent
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: parse-yaml-$RANDOM
      spec:
        input: "Read file: $FILE and extract section: $SECTION"
        target:
          type: agent
          name: chief-inspector
        timeout: 2m
      EOF
      kubectl apply -f /tmp/query.yaml
      kubectl wait --for=condition=Completed --timeout=2m query/...
      kubectl get query ... -o jsonpath='{.status.responses[0].content}'
```

### 4. Flows → Argo WorkflowTemplate

**LegacyX Flow Stage:**
```yaml
- name: extract-info
  target_type: group
  target_name: information_from_document
  target_version: v0.0.1
  input_values:
    - document_path: /path/to/doc.pdf
    - section: entities
  iterate_on: prompts_list
  iterator: prompt
```

**ARK Workflow Step:**
```yaml
- - name: extract-info-sequential
    when: "{{workflow.parameters.execution-mode}} == sequential"
    template: extract-info-sequential-template
    arguments:
      parameters:
        - name: prompts-json
          value: "{{steps.get-prompts.outputs.parameters.prompts-list}}"
        - name: document-file
          value: "{{workflow.parameters.document-file}}"

- name: extract-info-sequential-template
  inputs:
    parameters:
      - name: prompts-json
      - name: document-file
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      echo "$PROMPTS_JSON" | jq -r '.[]' | while read -r prompt; do
        QUERY_NAME="extract-$(date +%s%N)"
        cat > /tmp/query.yaml <<EOF
        apiVersion: ark.mckinsey.com/v1alpha1
        kind: Query
        metadata:
          name: $QUERY_NAME
        spec:
          input: |
            Document: $DOCUMENT_FILE
            Prompt: $prompt
            Extract and save to output file
          target:
            type: agent
            name: rag-agent
          timeout: 5m
        EOF
        kubectl apply -f /tmp/query.yaml
        kubectl wait --for=condition=Completed --timeout=5m query/$QUERY_NAME
      done
```

---

## Conventions & Patterns

### Convention 1: Team Composition Patterns

**Pattern 1: Worker + Critic (Quality Assurance)**
- **Use When:** LegacyX group includes a critic agent OR output quality is critical
- **Structure:** 2 agents, graph strategy, maxTurns: 3
- **Flow:** worker → critic → (conditional) → worker

```yaml
spec:
  strategy: graph
  maxTurns: 3
  members:
    - name: summary-agent
      type: agent
    - name: critic
      type: agent
  graph:
    edges:
      - from: summary-agent
        to: critic
      - from: critic
        to: summary-agent
```

**Pattern 2: Sequential Pipeline**
- **Use When:** Clear ordered steps without feedback loops
- **Structure:** N agents, sequential strategy
- **Flow:** agent1 → agent2 → agent3

**Pattern 3: Single Agent Query**
- **Use When:** Simple task, no review needed
- **Structure:** Direct Query to agent
- **No team needed**

### Convention 2: Agent Reuse Strategy

**Priority Order:**
1. **Existing ARK Agents** (check `/agents/` directory first)
2. **Modify Existing Agent** (if close match, adjust tools/prompts)
3. **Create New Agent** (only if no suitable agent exists)

**Agent Selection Confidence Levels:**
- ✅ **High Confidence (>90%):** Use existing agent directly
  - Example: LegacyX `information_from_document` → ARK `rag-agent`
  - Criteria: Same purpose, same tools available (RAG/PDF)
  
- ⚠️ **Medium Confidence (60-90%):** Test and potentially adjust
  - Example: LegacyX `web_data` → ARK `profile-web-enricher`
  - Criteria: Similar purpose, may need prompt adjustment
  
- ❌ **Low Confidence (<60%):** Create new or significant modification
  - Criteria: Different domain, missing tools, incompatible approach

**Available ARK Agents (Reference):**
- `rag-agent` - Document extraction with RAG tools
- `profile-web-enricher` - Web research and enrichment
- `companies-house-enricher` - UK company data, file operations
- `chief-inspector` - General analysis with file tools
- `summary-agent` - Summarization and consolidation
- `critic` - Quality review and feedback
- `web-agent` - General web operations
- `ubo-designer` - UBO graph creation
- Others in `/agents/` directory

### Convention 3: Execution Mode Parameterization

**Implement three execution modes: sequential, parallel, and fake (for testing):**
```yaml
spec:
  arguments:
    parameters:
      - name: execution-mode
        value: "fake"  # Default for rapid testing
        enum:
          - sequential  # Real agents, one at a time (15-30 min)
          - parallel    # Real agents, concurrent (10-20 min)  
          - fake        # No agents, direct file writes (2-3 min)
      
      - name: file-access-mode
        value: "http"  # Default for stability
        enum:
          - http   # HTTP server (recommended - stable, no mount issues)
          - mount  # Minikube mount (legacy - unstable, requires restarts)
      
      - name: document-file-http
        value: "http://host.docker.internal:8000/file.pdf"
      
      - name: document-file-mount
        value: "/mnt/output/source_code_files/data/file.pdf"
```

**File Access Mode Selection:**

HTTP Mode (Recommended):
```bash
# Start HTTP server in PDFs directory
cd /path/to/pdfs
python3 -m http.server 8000 &

# Workflow uses: http://host.docker.internal:8000/file.pdf
# Benefits: No mount crashes, no pod restarts, survives Mac sleep
```

Mount Mode (Legacy):
```bash
# Requires minikube mount (unstable)
minikube mount /path/to/output:/mnt/output &

# Workflow uses: /mnt/output/source_code_files/data/file.pdf
# Issues: Mount dies randomly, requires pod restarts, fails after sleep
```

**Dynamic File Path Selection:**
```yaml
# Step 0: Set document file based on mode
- name: set-document-file-script
  script:
    source: |
      if [ "$MODE" = "http" ]; then
        echo "{{workflow.parameters.document-file-http}}"
      else
        echo "{{workflow.parameters.document-file-mount}}"
      fi
```

**Fake Mode Implementation:**
For rapid workflow structure testing without agent delays, implement "fake" mode that:
- Writes placeholder JSON via `kubectl exec` to mcp-filesystem
- Skips agent query creation entirely
- Completes in minutes instead of hours
- Validates workflow structure, parameter passing, and file operations

```yaml
# In workflow steps - conditional execution
- - name: collect-info-sequential
    when: "{{workflow.parameters.execution-mode}} == sequential"
    template: collect-info-sequential
  
  - name: collect-info-parallel
    when: "{{workflow.parameters.execution-mode}} == parallel"
    template: collect-info-parallel
  
  - name: collect-info-fake
    when: "{{workflow.parameters.execution-mode}} == fake"
    template: collect-info-fake

# Fake template - direct kubectl exec to write test data
- name: collect-info-fake
  inputs:
    parameters:
      - name: prompts-json
      - name: output-dir
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      echo '$PROMPTS' | jq -r '.[]' | while read -r prompt; do
        HASH=$(echo "$prompt" | md5sum | cut -d' ' -f1)
        OUTPUT_FILE="/mnt/output/$OUTPUT_DIR/${HASH}.json"
        
        kubectl exec deployment/mcp-filesystem -- sh -c \
          "mkdir -p /mnt/output/$OUTPUT_DIR && cat > $OUTPUT_FILE" <<'EOF'
        {
          "extraction_status": "fake_test_data",
          "subsidiaries": [{"name": "Test Sub", "ownership_pct": 100}],
          "vessels": [{"name": "Test Vessel", "imo": "1234567"}]
        }
        EOF
      done
```

**In workflow steps:**
```yaml
- - name: process-sequential
    when: "{{workflow.parameters.execution-mode}} == sequential"
    template: sequential-template
  
  - name: process-parallel
    when: "{{workflow.parameters.execution-mode}} == parallel"
    template: parallel-template
```

**Rationale:**
- Sequential: Resource-constrained environments (local dev)
- Parallel: Production environments with resource availability

### Convention 4: File Operations via MCP Filesystem

**CRITICAL:** There are TWO separate filesystem MCP servers with different mount points:
1. **file-gateway-filesystem-mcp**: `/data/aas-files/` - Used by file-gateway API for uploads
2. **mcp-filesystem**: `/mnt/output/` - Used by agents via MCP tools AND Argo script containers

**IMPORTANT - Argo Output Parameter Capture:** When using Argo WorkflowTemplate script outputs, `/dev/stdout` is UNRELIABLE for output parameter capture. Always write to a temp file first:

```yaml
# ❌ UNRELIABLE - Argo can't capture stdout consistently
outputs:
  parameters:
    - name: file-paths
      valueFrom:
        path: /dev/stdout

# ✅ RELIABLE - Write to temp file first
source: |
  kubectl exec ... > /tmp/output.json
  cat /tmp/output.json
outputs:
  parameters:
    - name: file-paths
      valueFrom:
        path: /tmp/output.json
```

**For Deterministic Operations (Transformers like readdir, file parsing):**
Use direct volume mount in script containers - NO agents needed:

✅ **CORRECT - Direct volume mount for transformers:**
```yaml
- name: readdir-script
  script:
    image: alpine:latest
    volumeMounts:
      - name: mcp-filesystem-volume
        mountPath: /mnt/output
    source: |
      #!/bin/sh
      cd /mnt/output
      find source_code_files/... -type f -name "*.json"

# Add volume definition to WorkflowTemplate spec:
spec:
  volumes:
    - name: mcp-filesystem-volume
      hostPath:
        path: /mnt/output
        type: DirectoryOrCreate
```

**For AI-Driven File Operations (Agents reading/writing files):**
Agents access files through mcp-filesystem at paths relative to `/mnt/output/`:
- Agent path: `source_code_files/2-customer-due-diligence/input/file.yml`
- Actual location: `/mnt/output/source_code_files/2-customer-due-diligence/input/file.yml`

Use Query CRDs to agents/teams with mcp-filesystem tools:

✅ **CORRECT - Agent Query for AI operations:**
```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: extract-data-example
spec:
  input: |
    Read the file at: source_code_files/2-customer-due-diligence/input/document.pdf
    Extract all company names and save results to: source_code_files/output/extracted.json
  target:
    type: agent
    name: rag-agent
  timeout: 5m
```

❌ **INCORRECT - Using agents for deterministic file operations:**
```yaml
# DON'T use agents for simple file listing/parsing
# These are transformers, not AI tasks
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
spec:
  input: "List all .json files in directory..."
  target:
    type: agent
    name: some-agent
```

**Migration Rule:**
- **LegacyX Transformer** (deterministic) → ARK Script with volume mount
- **LegacyX Group** (AI task) → ARK Agent/Team Query

**Available mcp-filesystem tools for agents:**
- `mcp-filesystem-read-file` - Read file contents
- `mcp-filesystem-write-file` - Write file contents  
- `mcp-filesystem-list-directory` - List directory contents
- `mcp-filesystem-directory-tree` - Get directory tree structure
- `mcp-filesystem-search-files` - Search for files
- `mcp-filesystem-get-file-info` - Get file metadata
- `mcp-filesystem-create-directory` - Create directories
- `mcp-filesystem-move-file` - Move/rename files
- `mcp-filesystem-edit-file` - Edit existing files
- `mcp-filesystem-read-multiple-files` - Read multiple files at once

**File Upload:** Use kubectl cp to mcp-filesystem pod, not file-gateway API
```bash
# Find mcp-filesystem pod
MCP_POD=$(kubectl get pods -n default -l app.kubernetes.io/name=filesystem-mcp -o jsonpath='{.items[0].metadata.name}')

# Create directory
kubectl exec -n default $MCP_POD -- mkdir -p /mnt/output/source_code_files/2-customer-due-diligence/input

# Copy file
kubectl cp prompts.yml default/$MCP_POD:/mnt/output/source_code_files/2-customer-due-diligence/input/prompts.yml
```

**Verify mcp-filesystem allowed directory:**
```bash
kubectl get pod -l app.kubernetes.io/name=filesystem-mcp -n default -o yaml | grep -A 2 ALLOWED_DIRECTORIES
# Should show: ALLOWED_DIRECTORIES=/mnt/output
```

### Convention 5: Prompt/Goal Passing

**LegacyX Approach (Embedded):**
```yaml
group:
  goal: "Extract all subsidiaries with ownership >25%"
```

**ARK Approach (Runtime Input):**
```yaml
spec:
  input: |
    Extract all subsidiaries with ownership >25%
    
    Company: {{company_name}}
    Document: {{document_file}}
    
    Output format: JSON array
    Save to: {{output_file}}
```

**Guideline:** All prompts/goals/instructions passed as Query `input` field at execution time

---

## Pre-Migration Checklist

Before starting any migration, gather this information:

**From LegacyX Flow:**
- [ ] Flow name and version
- [ ] All stages (names, types, order)
- [ ] All input parameters/values
- [ ] All output values
- [ ] All file paths (input/output)
- [ ] All transformers used (list with versions)
- [ ] All groups used (list with versions)
- [ ] Iteration patterns (which stages iterate, over what)
- [ ] Dependencies between stages

**From LegacyX Components:**
- [ ] Extract transformer bundles (`.lxtf` files if custom)
- [ ] Locate group definitions
- [ ] Find all referenced files (prompts, configs, etc.)
- [ ] Document any special configurations

**ARK Environment:**
- [ ] List available agents: `kubectl get agents -n default`
- [ ] List available teams: `kubectl get teams -n default`
- [ ] List available MCP servers: `kubectl get mcpserver -n default`
- [ ] Check model availability: `kubectl get agents | grep True`
- [ ] Verify file-gateway is running: `kubectl get pods -l app=file-gateway`

---

## Migration Process

### Step 1: Analyze LegacyX Flow
1. Read `flow.yaml` completely
2. Create stage inventory:
   ```
   Stage Name | Type (transformer/group) | Iterates? | Input Values | Output Values
   -----------|-------------------------|-----------|--------------|---------------
   stage-1    | transformer: get_date   | No        | -            | current_date
   stage-2    | group: extract_info     | Yes       | doc, prompts | extracted_data
   ```
3. Classify each stage:
   - Transformer → Deterministic or AI-required?
   - Group → Single agent or team needed?
   - Iteration → Sequential or parallel or both?
4. Draw data flow diagram (manual or mental map)
5. Identify all file dependencies

### Step 2: Map to ARK Resources

**For Each Transformer:**
1. Check if deterministic (date, math, JSON ops) or AI-required
2. If deterministic: Plan shell script with appropriate image (alpine, jq, yq)
3. If AI-required: Select agent with needed capabilities
4. Document in mapping table

**For Each Group:**
1. Review group goal/purpose
2. Check existing agents (confidence level assessment)
3. Decision:
   - Single agent if simple task
   - 2-agent team if critic needed
   - Multi-agent team if complex
4. Document in mapping table

**Create Resource Map:**
```
LegacyX Stage → ARK Solution → Confidence → Action Needed
stage-1       → rag-agent     → High (95%) → None (exists)
stage-2       → new-team      → Medium      → Create team
```

### Step 3: Create Missing ARK Resources

**If New Agent Needed:**
```bash
# Create agent YAML referencing existing model and tools
kubectl apply -f agents/new-agent.yaml
# Test with simple query
kubectl create -f - <<EOF
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: test-agent-$(date +%s)
spec:
  input: "Simple test task"
  target:
    type: agent
    name: new-agent
  timeout: 2m
EOF
```

**If New Team Needed:**
```bash
# Ensure all member agents exist first
kubectl get agent worker-agent critic-agent
# Create team
kubectl apply -f teams/new-team.yaml
# Test with simple query
```

### Step 4: Design WorkflowTemplate Structure

**Workflow Template Skeleton:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: [flow-name]
spec:
  entrypoint: main
  serviceAccountName: argo-workflow
  arguments:
    parameters:
      # Map from LegacyX input_values
      - name: execution-mode
        value: "sequential"
        enum: ["sequential", "parallel"]
  templates:
    - name: main
      steps:
        # One step per LegacyX stage
        # Conditional steps for sequential/parallel
    
    # Template for each transformer
    - name: transformer-1-script
      # ... implementation
    
    # Template for each group (as query)
    - name: group-1-query
      # ... implementation
```

**For Each Stage, Create Template:**
1. Transformer → Script template
2. Group → Query template (or team query)
3. If iterates → Add loop logic or withParam
4. Wire outputs to next stage inputs

### Step 5: Implement Workflow Templates

**Template Implementation Order:**
1. Start with simple transformers (date, JSON ops)
2. Add group query templates
3. Implement iteration logic
4. Add conditional sequential/parallel execution
5. Wire together with parameters
6. Add error handling (check Query phase)

**Testing Each Template:**
```bash
# Create minimal workflow to test one template
kubectl create -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-
spec:
  entrypoint: test-template
  templates:
    - name: test-template
      template: [your-template-name]
      arguments:
        parameters:
          - name: test-param
            value: "test-value"
EOF
```

### Step 6: Handle Files

**Upload Input Files:**
```bash
# Port forward to file-gateway API
kubectl port-forward svc/file-gateway-api 8181:80 &
sleep 2

# Upload each file
for file in prompts.yml config.json; do
  curl -X POST http://localhost:8181/files \
    -F "file=@$file" \
    -F "prefix=/path/in/gateway/"
done

# Kill port-forward
pkill -f "port-forward.*file-gateway"
```

**Verify Files Uploaded:**
```bash
# Create query to list files
kubectl create -f - <<EOF
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: list-files-$(date +%s)
spec:
  input: "List all files in /path/in/gateway/ recursively"
  target:
    type: agent
    name: companies-house-enricher
  timeout: 1m
EOF

# Check response
kubectl get query list-files-* -n default --sort-by=.metadata.creationTimestamp | tail -1
kubectl get query [query-name] -o yaml | grep content -A 5
```

### Step 7: Deploy and Test

**Deployment:**
```bash
# Deploy teams first
kubectl apply -f teams/

# Deploy workflow template
kubectl apply -f argo-workflows/[workflow-name].yaml

# Verify
kubectl get workflowtemplate [workflow-name]
```

**Testing (Sequential Mode):**
```bash
# Create workflow instance
kubectl create -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: [workflow-name]-
spec:
  workflowTemplateRef:
    name: [workflow-name]
  arguments:
    parameters:
      - name: execution-mode
        value: "sequential"
      # ... other parameters
EOF

# Monitor
kubectl get workflow -n default -w

# Check specific workflow
WORKFLOW=$(kubectl get workflow -n default --sort-by=.metadata.creationTimestamp | tail -1 | awk '{print $1}')
kubectl get workflow $WORKFLOW -n default

# Check for errors
kubectl get workflow $WORKFLOW -o yaml | grep -A 10 "message:"
```

**Debugging Failed Steps:**
```bash
# Find failed step
kubectl get workflow $WORKFLOW -o jsonpath='{.status.nodes}' | \
  jq -r 'to_entries[] | select(.value.phase == "Failed" or .value.phase == "Error") | .value.displayName'

# Get pod logs
kubectl get pods -l workflows.argoproj.io/workflow=$WORKFLOW
kubectl logs [pod-name] -c main

# Check Query failures
kubectl get query -n default --sort-by=.metadata.creationTimestamp | grep error | tail -5
kubectl describe query [query-name]
```

### Step 8: Validate Results

**Validation Checklist:**
- [ ] Workflow completed successfully
- [ ] All expected output files created
- [ ] Output files in correct locations
- [ ] Output content matches expected format
- [ ] All Query CRDs completed (no errors)
- [ ] Execution time reasonable
- [ ] Resource usage acceptable

**Compare with LegacyX:**
- [ ] Same number of stages executed
- [ ] Similar execution time (±20%)
- [ ] Output files contain equivalent data
- [ ] No missing information

**Test Parallel Mode:**
```bash
# Create workflow with parallel mode
kubectl create -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: [workflow-name]-parallel-
spec:
  workflowTemplateRef:
    name: [workflow-name]
  arguments:
    parameters:
      - name: execution-mode
        value: "parallel"
EOF

# Verify parallel execution (multiple queries at once)
kubectl get query -n default -w
```

---

## Reusable Workflow Template Snippets

### Snippet 1: Workflow Header with Parameters
```yaml
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: [flow-name]
  annotations:
    workflows.argoproj.io/title: "[Human Readable Title]"
    workflows.argoproj.io/description: "[Description]"
    workflows.argoproj.io/version: "v0.0.1"
spec:
  entrypoint: main
  serviceAccountName: argo-workflow
  arguments:
    parameters:
      - name: execution-mode
        value: "sequential"
        enum: ["sequential", "parallel"]
      # Add your flow-specific parameters here
```

### Snippet 2: Conditional Sequential/Parallel Step
```yaml
# In main workflow steps:
- - name: process-data-sequential
    when: "{{workflow.parameters.execution-mode}} == sequential"
    template: process-sequential
    arguments:
      parameters:
        - name: input-data
          value: "{{steps.previous-step.outputs.parameters.output}}"
  
  - name: process-data-parallel
    when: "{{workflow.parameters.execution-mode}} == parallel"
    template: process-parallel
    arguments:
      parameters:
        - name: input-data
          value: "{{steps.previous-step.outputs.parameters.output}}"
```

### Snippet 3: Sequential Loop Processing
```yaml
- name: process-sequential
  inputs:
    parameters:
      - name: items-json  # JSON array
      - name: other-param
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      set -eux
      ITEMS='{{inputs.parameters.items-json}}'
      
      echo "$ITEMS" | jq -r '.[]' | while IFS= read -r item; do
        QUERY_NAME="process-$(date +%s%N)"
        
        cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: $QUERY_NAME
      spec:
        input: |
          Process: $item
          Other param: {{inputs.parameters.other-param}}
        target:
          type: agent
          name: [agent-name]
        timeout: 5m
      EOF
        
        kubectl apply -n default -f /tmp/query.yaml
        kubectl wait --for=condition=Completed --timeout=5m -n default query/$QUERY_NAME || true
        
        PHASE=$(kubectl get query $QUERY_NAME -n default -o jsonpath='{.status.phase}')
        if [ "$PHASE" = "error" ]; then
          echo "Error processing: $item"
        else
          echo "Success: $item"
        fi
      done
```

### Snippet 4: Parallel Processing with withParam
```yaml
- name: process-parallel
  inputs:
    parameters:
      - name: items-json
      - name: other-param
  steps:
    - - name: process-item
        template: process-single-item
        arguments:
          parameters:
            - name: item
              value: "{{item}}"
            - name: other-param
              value: "{{inputs.parameters.other-param}}"
        withParam: "{{inputs.parameters.items-json}}"

- name: process-single-item
  inputs:
    parameters:
      - name: item
      - name: other-param
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      QUERY_NAME="process-{{workflow.name}}-$(date +%s%N)"
      
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: $QUERY_NAME
      spec:
        input: |
          Process: {{inputs.parameters.item}}
          Other: {{inputs.parameters.other-param}}
        target:
          type: agent
          name: [agent-name]
        timeout: 5m
      EOF
      
      kubectl apply -n default -f /tmp/query.yaml
      kubectl wait --for=condition=Completed --timeout=5m -n default query/$QUERY_NAME
```

### Snippet 5: Agent Query with Error Handling
```yaml
- name: query-agent-template
  inputs:
    parameters:
      - name: input-prompt
      - name: agent-name
      - name: timeout
        value: "5m"
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      set -eux
      
      QUERY_NAME="query-{{workflow.name}}-$(date +%s%N)"
      
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: $QUERY_NAME
        labels:
          workflow: "{{workflow.name}}"
      spec:
        input: |
          {{inputs.parameters.input-prompt}}
        target:
          type: agent
          name: {{inputs.parameters.agent-name}}
        serviceAccount: argo-workflow
        timeout: {{inputs.parameters.timeout}}
      EOF
      
      kubectl apply -n default -f /tmp/query.yaml
      kubectl wait --for=condition=Completed --timeout={{inputs.parameters.timeout}} -n default query/$QUERY_NAME || true
      
      kubectl get query $QUERY_NAME -n default -o json > /tmp/query.json
      PHASE=$(jq -r '.status.phase' /tmp/query.json)
      
      if [ "$PHASE" = "error" ]; then
        ERROR_MSG=$(jq -r '.status.responses[0].content // .status.error // "Unknown error"' /tmp/query.json)
        echo "ERROR: $ERROR_MSG" >&2
        echo "Error occurred"
        exit 1
      fi
      
      jq -r '.status.responses[0].content // ""' /tmp/query.json | tee /tmp/response.txt
  outputs:
    parameters:
      - name: response
        valueFrom:
          path: /tmp/response.txt
```

### Snippet 6: Team Query (with iterations)
```yaml
- name: query-team-template
  inputs:
    parameters:
      - name: input-prompt
      - name: team-name
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      set -eux
      
      QUERY_NAME="team-query-{{workflow.name}}-$(date +%s%N)"
      
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: $QUERY_NAME
      spec:
        input: |
          {{inputs.parameters.input-prompt}}
        target:
          type: team
          name: {{inputs.parameters.team-name}}
        serviceAccount: argo-workflow
        timeout: 10m
      EOF
      
      kubectl apply -n default -f /tmp/query.yaml
      kubectl wait --for=condition=Completed --timeout=10m -n default query/$QUERY_NAME || true
      
      kubectl get query $QUERY_NAME -n default -o json | \
        jq -r '.status.responses[0].content // ""' | \
        tee /tmp/response.txt
  outputs:
    parameters:
      - name: response
        valueFrom:
          path: /tmp/response.txt
```

### Snippet 7: Deterministic Transformer (Date)
```yaml
- name: get-current-date-script
  script:
    image: alpine:3.19
    command: [sh]
    source: |
      date +"%Y-%m-%d"
```

### Snippet 8: File Read via Agent
```yaml
- name: read-file-via-agent
  inputs:
    parameters:
      - name: file-path
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      QUERY_NAME="read-file-$(date +%s%N)"
      
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: $QUERY_NAME
      spec:
        input: |
          Read the file: {{inputs.parameters.file-path}}
          
          Return the complete content.
          
          Use file-gateway-mcpserver-read-file tool.
        target:
          type: agent
          name: companies-house-enricher
        timeout: 2m
      EOF
      
      kubectl apply -n default -f /tmp/query.yaml
      kubectl wait --for=condition=Completed --timeout=2m -n default query/$QUERY_NAME
      kubectl get query $QUERY_NAME -o jsonpath='{.status.responses[0].content}'
  outputs:
    parameters:
      - name: file-content
        valueFrom:
          path: /dev/stdout
```

### Snippet 9: Combine JSON Files with jq
```yaml
- name: combine-json-files
  inputs:
    parameters:
      - name: file-paths-json  # JSON array of file paths
      - name: output-file
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      QUERY_NAME="combine-json-$(date +%s%N)"
      FILE_PATHS='{{inputs.parameters.file-paths-json}}'
      OUTPUT='{{inputs.parameters.output-file}}'
      
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      metadata:
        name: $QUERY_NAME
      spec:
        input: |
          Read all JSON files in this list: $FILE_PATHS
          
          Merge them into a single JSON array or object (as appropriate).
          
          Write the combined result to: $OUTPUT
          
          Use file-gateway tools to read and write.
        target:
          type: agent
          name: companies-house-enricher
        timeout: 5m
      EOF
      
      kubectl apply -n default -f /tmp/query.yaml
      kubectl wait --for=condition=Completed --timeout=5m -n default query/$QUERY_NAME
```

### Snippet 10: Final Results Display
```yaml
- name: display-results
  inputs:
    parameters:
      - name: final-output
      - name: output-file-path
  script:
    image: alpine:3.19
    command: [sh]
    source: |
      echo "========================================================================"
      echo "WORKFLOW COMPLETE: {{workflow.name}}"
      echo "========================================================================"
      echo "Completed: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
      echo ""
      echo "Output saved to: {{inputs.parameters.output-file-path}}"
      echo ""
      echo "========================================================================"
      echo "RESULTS"
      echo "========================================================================"
      echo "{{inputs.parameters.final-output}}"
      echo ""
      echo "========================================================================"
```

---

## Common Migration Patterns

### Pattern A: Simple Sequential Processing Flow
**LegacyX:** Stages with no iteration, sequential execution
**ARK:** Simple workflow steps, no conditional execution needed

```yaml
templates:
  - name: main
    steps:
      - - name: step1
          template: transformer-1
      - - name: step2
          template: query-agent-1
          arguments:
            parameters:
              - name: input
                value: "{{steps.step1.outputs.result}}"
      - - name: step3
          template: transformer-2
```

### Pattern B: Iterated Processing with Conditional Execution
**LegacyX:** Stage with `iterate_on`, need for resource control
**ARK:** Conditional sequential/parallel templates

```yaml
templates:
  - name: main
    steps:
      - - name: get-items
          template: get-items-list
      
      - - name: process-sequential
          when: "{{workflow.parameters.execution-mode}} == sequential"
          template: process-seq-loop
      
        - name: process-parallel
          when: "{{workflow.parameters.execution-mode}} == parallel"
          template: process-parallel-withparam
```

### Pattern C: Multi-Stage with File Operations
**LegacyX:** Stages reading/writing files, transformers manipulating data
**ARK:** Agent queries for file ops, script templates for manipulation

```yaml
templates:
  - name: main
    steps:
      - - name: read-config
          template: read-file-via-agent
      
      - - name: process-data
          template: query-agent-with-config
      
      - - name: write-results
          template: write-file-via-agent
```

### Pattern D: Consolidation with Review
**LegacyX:** Group with main agent and critic
**ARK:** Team Query with 2 agents (graph strategy)

```yaml
templates:
  - name: main
    steps:
      - - name: consolidate
          template: query-consolidation-team
          arguments:
            parameters:
              - name: input-data
                value: "{{steps.collect-data.outputs.result}}"

  - name: query-consolidation-team
    # Use team query snippet with team that has worker + critic
```

---

## Agent Selection Decision Tree

```
Start: Need to execute LegacyX group
│
├─ Is this a simple, well-defined task? (e.g., "extract from PDF")
│  YES → Check existing agents for capability match
│  │     ├─ Exact match found? → Use that agent (Confidence: High)
│  │     ├─ Close match found? → Test agent, adjust prompt (Confidence: Medium)
│  │     └─ No match? → Create new agent
│  NO → Continue to next check
│
├─ Does the group include a critic/reviewer role?
│  YES → Create/use 2-agent team (worker + critic, graph strategy)
│  NO → Continue to next check
│
├─ Does the task require multiple specialized skills?
│  YES → Create multi-agent team with orchestration
│  NO → Use single agent with comprehensive prompt
│
└─ Final: Document your decision and confidence level
```

**Capability Matching Guide:**
- Document extraction/RAG → `rag-agent` (High confidence)
- Web research → `profile-web-enricher` or `web-agent` (Medium-High)
- File operations → `companies-house-enricher` or `chief-inspector` (High)
- Summarization → `summary-agent` (High)
- Review/critique → `critic` (High)
- UBO analysis → `ubo-designer` (Medium, domain-specific)
- General analysis → `chief-inspector` or `main-agent` (Medium)

---

## Best Practices

### 1. Error Handling in Workflows
Always check Query phase and handle errors:
```bash
PHASE=$(kubectl get query $QUERY_NAME -n default -o jsonpath='{.status.phase}')
if [ "$PHASE" = "error" ]; then
  ERROR_MSG=$(kubectl get query $QUERY_NAME -n default -o jsonpath='{.status.responses[0].content}')
  echo "ERROR: $ERROR_MSG" >&2
  exit 1
fi
```

### 2. Timeouts
Set appropriate timeouts based on operation:
- Simple queries: 2m
- Document extraction: 5m
- Web research: 8m
- Team with iterations: 10m

### 3. Output Capture
- Simple strings: `outputs.result` (stdout)
- Complex JSON: `valueFrom.path: /tmp/output.json`
- Always use `tee` to capture to file for debugging

### 4. Query Naming
Use timestamps for uniqueness:
```bash
QUERY_NAME="operation-name-$(date +%s%N)"
```

### 5. Tool Verification
Before using an agent, verify it has required tools:
```bash
kubectl get agent $AGENT_NAME -n default -o yaml | grep "tools:"
```

### 6. Model Availability
Check agent model availability before deployment:
```bash
kubectl get agents -n default | grep -E "agent-name.*True"
```

### 7. Prompt Engineering for Agents
When passing prompts to agents:
- Be explicit about output format (JSON, Markdown, etc.)
- Specify file operations clearly (read X, write Y)
- Include examples when format is critical
- Use "CRITICAL:" or "IMPORTANT:" for key requirements

### 8. Query Input: Declarative vs Imperative (CRITICAL)

**Use Declarative Queries (WHAT not HOW):**

❌ **Wrong - Imperative (specifies HOW):**
```yaml
spec:
  input: |
    Use the `analyze_pdf_ownership` tool to extract information from the PDF.
    After extraction, use the `write-file` tool to save the JSON.
  target:
    type: agent
    name: rag-agent
```

✅ **Correct - Declarative (specifies WHAT):**
```yaml
spec:
  input: |
    Extract ownership information from the PDF at: {{.pdf_url}}
    
    Identify all beneficial owners with ownership percentages above 25%.
    
    Save the results to: /mnt/output/{{.output_file}}
  target:
    type: team
    name: scout-rag-team
```

**Why Declarative is Better:**
- Agents/teams decide which tools to use based on their capabilities
- More flexible - works if tool names change
- Teams can coordinate tool usage (scout finds content, RAG extracts it)
- Easier to maintain and understand

**Target Selection:**
- Use `type: team` for complex document extraction (`scout-rag-team`)
- Use `type: agent` with appropriate agent:
  - `consolidation-agent` - Analysis, consolidation, file operations
  - `profile-web-enricher` - Web research, enrichment
  - `rag-agent` - Simple document queries (but prefer scout-rag-team)
  - `summary-agent` - Summarization tasks

### 9. Team-Based Document Extraction

**Prefer Teams over Single Agents for PDF extraction:**

```yaml
# Two-stage extraction with scout-rag-team
spec:
  input: |
    Analyze the PDF document at: {{.document_url}}
    Company: {{.company_name}}
    
    Extract ownership structure including:
    - Direct beneficial owners
    - Ownership percentages
    - Jurisdiction information
    
    Save results to: /mnt/output/{{.output_file}}
  target:
    type: team
    name: scout-rag-team  # Scout finds pages, RAG extracts content
  timeout: 15m
```

**Benefits:**
- Scout agent scans entire PDF, finds all ownership-related pages
- RAG agent uses targeted queries for better chunk retrieval
- More comprehensive extraction than single-agent approach

---

## Known Issues & Solutions

### Issue 1: Agent Returns Wrong Format
**Problem:** Agent returns markdown instead of JSON
**Solution:** Add explicit format instructions and strip markdown:
```bash
kubectl get query $Q -o jsonpath='{.status.responses[0].content}' | \
  sed 's/^```json//g' | sed 's/^```//g' | sed 's/```$//g'
```

### Issue 2: 403 Forbidden on Model
**Problem:** `gpt5` model returns 403 Forbidden
**Solution:** 
1. Update model credentials/token
2. Use agents with `azure-openai-model` as fallback
3. Check model availability before deployment

### Issue 3: Empty File Lists
**Problem:** `readdir` returns empty array
**Solution:**
1. Verify previous steps actually created files
2. Check agent actually wrote files (not just responded)
3. Use explicit file write instructions: "Use file-gateway-mcpserver-write-file tool"

### Issue 4: File Not Found
**Problem:** Workflow can't access uploaded files
**Solution:**
1. Upload via file-gateway API (not PVC directly)
2. Verify path matches exactly (include leading slash)
3. Use agent with file tools to verify file exists

### Issue 5: Workflow Hangs on Script Step
**Problem:** Script step runs for hours without progress
**Solution:**
1. Check if `kubectl wait` timed out (increase timeout)
2. Check Query status manually: `kubectl get query $NAME`
3. Add `set -eux` for debugging output
4. Use `|| true` to prevent early exit on expected failures

### Issue 7: YAML Heredoc Injection Breaks with Newlines
**Symptom:** `error parsing /tmp/query.yaml: error converting YAML to JSON: yaml: line X: could not find expected ':'`
**Problem:** Multi-line JSON arrays inserted into YAML heredoc break syntax
**Example:**
```bash
FILE_PATHS='["file1.json",
"file2.json"]'  # Multi-line

cat > /tmp/query.yaml <<EOF
input: |
  Process these files: $FILE_PATHS  # Newline breaks YAML!
EOF
```
**Solution:** Compact JSON to single line before inserting:
```bash
FILE_PATHS='["file1.json","file2.json"]'  # From previous step
FILE_PATHS_COMPACT=$(echo "$FILE_PATHS" | tr -d '\n' | tr -s ' ')  # Remove newlines

cat > /tmp/query.yaml <<EOF
input: |
  Process these files: $FILE_PATHS_COMPACT  # Single line works!
EOF
```

### Issue 8: Team Query Timeout Too Short for Consolidation
**Symptom:** Team query fails with `agent default/X execution failed: context deadline exceeded`
**Problem:** Timeout too short for:
  - File reading via mcp-filesystem (~1-2min)
  - Agent processing and consolidation (~2-5min per agent)
  - Critic review (~1-2min)
  - File writing via mcp-filesystem (~1min)
**Solution:** Set timeout based on task complexity:
```yaml
# ❌ TOO SHORT for consolidation tasks
timeout: 5m

# ✅ APPROPRIATE for file read + multi-agent processing + write
timeout: 15m

# General guidance:
# - Simple query (no files): 2-5m
# - Single agent with files: 5-10m  
# - Team with files: 15-20m
# - Complex team iterations: 20-30m
```
**Evidence:** rag-agent with 15m timeout successfully extracted data; consolidation team needed 7m32s (failed with 5m, succeeded with 15m)

### Issue 6: "Path outside allowed directory" Error
**Symptom:** File operations fail with error message "Path outside allowed directory", OR `readdir` returns empty array `[]` even though files were created
**Root Cause:** File-gateway MCP server only allows access to `/data/aas-files/` directory. Using any other base path (like `/source_code_files/`) will fail.
**Impact:** Affects ALL file operations:
- Agents saving files (doc-extract, web-enricher writes)
- Agents reading files  
- Directory listings (readdir, list-directory)
- File uploads via API

**Solution:** Change all file paths to start with `/data/aas-files/`
```yaml
# ❌ WRONG - will fail with "Path outside allowed directory"
output-base-dir: "/source_code_files/2-customer-due-diligence"

# ✅ CORRECT - allowed path
output-base-dir: "/data/aas-files/2-customer-due-diligence"
```

**Debugging Commands:**
```bash
# 1. Check file-gateway allowed directory
kubectl logs -n default $(kubectl get pods -n default | grep file-gateway-filesystem-mcp | awk '{print $1}') \
  | grep -i "allowed\|Setting base"
# Expected: Using allowed directories [ '/data/aas-files' ]

# 2. Test file access with agent
QUERY_NAME="test-file-$(date +%s)" && cat <<EOF | kubectl apply -f -
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: \$QUERY_NAME
spec:
  input: |
    List all files in directory: /data/aas-files/
    Use file-gateway tools.
  target:
    type: agent
    name: companies-house-enricher
  timeout: 1m
EOF

# 3. Check if files exist in correct location
kubectl exec -it $(kubectl get pods | grep file-gateway-filesystem-mcp | awk '{print $1}') \
  -- ls -la /data/aas-files/
```

**Common Mistake:** Copying paths from other workflows without checking file-gateway configuration. Always verify the allowed base directory first.

---

## Tools & Transformers Migration Guide

### When You Encounter a Tool/Transformer

**Step 1: Identify Type**
- Is it deterministic? (date, math, file ops, JSON manipulation)
- Does it require AI? (parsing natural language, understanding context)

**Step 2: Check for Equivalent**
- LegacyX Built-ins: Check if ARK has MCP tool equivalent
- Custom Transformers: Extract from `.lxtf` bundle, analyze implementation

**Step 3: Migration Path**

**For Deterministic:**
```yaml
- name: transformer-name
  script:
    image: alpine:3.19  # or jq, yq as needed
    command: [sh]
    source: |
      # Shell script implementation
```

**For AI-Required:**
```yaml
- name: transformer-name
  script:
    image: alpine/k8s:1.28.13
    command: [sh]
    source: |
      # Create ARK Query to agent with appropriate tools
      cat > /tmp/query.yaml <<EOF
      apiVersion: ark.mckinsey.com/v1alpha1
      kind: Query
      ...
      EOF
      kubectl apply -f /tmp/query.yaml
      kubectl wait --for=condition=Completed ...
```

**Step 4: Document in This File**
Add the transformer mapping to the "Transformer Mappings" section

---

## Transformer Mappings (Learned)

| LegacyX Transformer | Type | ARK Implementation | Image | Notes |
|---------------------|------|-------------------|-------|-------|
| `get_current_date` | Deterministic | Shell `date` command | `alpine:3.19` | Captures stdout |
| `yaml_to_list` | AI-Required | Agent Query (file read + parse) | `alpine/k8s:1.28.13` | Hardcoded for now, agent unreliable |
| `readdir` | Deterministic | `kubectl exec` to mcp-filesystem | `alpine/k8s:1.28.13` | Direct find command, output to temp file |
| `combine_json` | AI-Required | Agent Query via `alpine/k8s` | `alpine/k8s:1.28.13` | Use alpine/k8s, not stedolan/jq (image pull issues) |
| `parse_json` | Deterministic | `jq` command | TBD | Not yet migrated |
| `concat_files` | Deterministic | Shell `cat` | TBD | Not yet migrated |

---

## Group Mappings (Learned)

| LegacyX Group | ARK Solution | Type | Confidence | Notes |
|---------------|--------------|------|------------|-------|
| `information_from_document` | `rag-agent` Query | Single Agent | ✅ High (95%) | RAG tools available |
| `web_data` | `profile-web-enricher` Query | Single Agent | ⚠️ Medium (75%) | Test web tools |
| `consolidation` | `entities-vessels-consolidation-team` | Team (2 agents) | ✅ High (90%) | summary + critic pattern |

---

## Update Log

### 2026-02-05: Initial Migration (retrieve_entities_vessels)
- **Completed:** Full translation of `retrieve_entities_vessels` flow
- **Learned:** File access via file-gateway, not PVC mounts
- **Learned:** Hardcode prompts when agent parsing unreliable
- **Learned:** Model availability critical (gpt5 403 errors)
- **Learned:** Agent name precision (`profile-web-enricher` not `-agent`)
- **Created:** `entities-vessels-consolidation-team` (2-agent, graph, maxTurns: 3)
- **Pattern:** Sequential/parallel parametric execution
- **Files:** 
  - `/argo-workflows/retrieve-entities-vessels-workflow.yaml` (621 lines)
  - `/teams/entities-vessels-consolidation-team.yaml`
  - `/docs/TRANSLATION_SUMMARY.md`

### 2026-02-05: Critical File Path Discovery
- **CRITICAL FINDING:** File-gateway root is `/data/aas-files/`, NOT `/source_code_files/`
- **Issue:** Workflows hanging on `readdir` with empty array `[]` results
- **Root Cause:** Wrong base path causing "Path outside allowed directory" errors
- **Impact:** ALL file operations (read/write/list) must use `/data/aas-files/` prefix
- **Fixed:** Updated workflow template `output-base-dir` parameter
- **Debugging:** Added file-gateway path verification commands to guide
- **Documentation:** Enhanced Convention 4 and added Issue 6 with detailed debugging steps

### 2026-02-09: Workflow Completion - Fake Mode & Timeout Fixes
- **MAJOR SUCCESS:** retrieve_entities_vessels workflow completed end-to-end (8/8 steps)
- **Duration:** 9m48s total execution time
- **Consolidation:** Team query completed in 7m32s (within 15m timeout)
- **Output:** 7.5KB consolidated JSON file created successfully

**Issues Fixed:**
1. **readdir Output Capture:** Changed from `/dev/stdout` (unreliable) to `/tmp/file-paths.json` (reliable)
   - Root Cause: Argo WorkflowTemplate can't consistently capture stdout for output parameters
   - Solution: Write to temp file first, then cat to stdout
   - Impact: Fixed "workflow stuck on running step" issue (pod completed but Argo didn't capture output)

2. **YAML Heredoc Injection:** Added JSON compacting to prevent newline syntax errors
   - Root Cause: Multi-line JSON arrays broke YAML syntax when inserted via heredoc
   - Solution: `FILE_PATHS_COMPACT=$(echo "$FILE_PATHS" | tr -d '\n' | tr -s ' ')`
   - Error: `error parsing /tmp/query.yaml: yaml: line 9: could not find expected ':'`

3. **Image Pull Failure:** Changed combine-json image from `stedolan/jq:latest` to `alpine/k8s:1.28.13`
   - Root Cause: stedolan/jq:latest image not accessible in environment
   - Solution: Use alpine/k8s (already used throughout workflow)
   - Impact: Fixed ImagePullBackOff blocking workflow progress

4. **Team Query Timeout:** Increased consolidation timeout from 5m to 15m
   - Root Cause: 5m insufficient for file reading + multi-agent processing + file writing
   - Evidence: Query timed out at exactly 5m0.03s with "context deadline exceeded" error
   - Solution: 15m timeout (team completed in 7m32s with 7.5m buffer)
   - Impact: Team query now completes successfully without timeout

**Fake Execution Mode Implemented:**
- **Purpose:** Rapid workflow structure testing without agent query delays
- **Speed:** 2-3 minutes vs 15-30 minutes for sequential mode
- **Method:** Direct `kubectl exec` writes to mcp-filesystem, no agent queries created
- **Use Case:** Testing workflow structure, parameter passing, file operations, and step sequencing
- **Templates Added:**
  - `collect-info-fake`: Writes placeholder subsidiary/vessel JSON
  - `collect-web-data-fake`: Writes placeholder web research JSON
- **Conditional Execution:** Three modes via `execution-mode` parameter (sequential/parallel/fake)

**Technical Learnings:**
- **Argo Output Parameters:** `/dev/stdout` unreliable, use temp files
- **YAML Heredoc Injection:** Compact JSON before insertion to avoid newline breaks
- **Image Selection:** Use `alpine/k8s:1.28.13` throughout (has kubectl, works reliably)
- **Team Timeouts:** Base on task complexity (consolidation needs 15-20m minimum)
- **Fake Mode Pattern:** Direct kubectl exec for instant testing (bypasses agent system)
- **Query Cleanup:** Agent pods terminate immediately after timeout, logs unavailable
- **Sub-query Investigation:** Empty subqueries array means timeout before team execution started

**Workflow Architecture Validated:**
```
Step 1: Get current date (script) → 2s
Step 2: Get prompts (script/hardcoded) → 2s  
Step 3: Collect document info (agent/fake) → 2-15m
Step 4: Collect web data (agent/fake) → 2-8m
Step 5: List JSON files (script/readdir) → 5s
Step 6: Combine JSON (agent query) → 2-5m
Step 7: Consolidate (team query) → 7m32s
Step 8: Process results (script) → 2s

Total (fake mode): ~3min
Total (sequential mode): ~25-45min
Total (parallel mode): ~15-25min
```

**Files:**
- `/argo-workflows/lx-retrieve-entities-vessels-workflow.yaml` (717 lines)
  - Added fake mode templates (lines 315-465)
  - Fixed readdir output (lines 195-210)
  - Fixed combine-json YAML/image (lines 214-231)  
  - Fixed team timeout (line 656: 5m → 15m, line 661: 5m → 15m)
- Output: `/mnt/output/source_code_files/2-customer-due-diligence/profile_sections/entities_vessels.json` (7.5KB)

### Key Learnings Summary
1. **File Paths:** Two MCP servers: file-gateway (`/data/aas-files/`) vs mcp-filesystem (`/mnt/output/`)
2. **Argo Output Capture:** `/dev/stdout` unreliable for parameters, use temp files
3. **YAML Heredoc:** Compact JSON before insertion (`tr -d '\n'`) to avoid newline syntax breaks
4. **Team Timeouts:** 15-20m for consolidation tasks (file reading + multi-agent + file writing)
5. **Fake Mode:** Direct kubectl writes for rapid testing (2-3min vs 15-30min)
6. **Team Schema:** `members`/`graph`/`maxTurns`, not `agents`/`flow`/`maxIterations`
7. **Agent Naming:** Exact matches required (no suffixes)
8. **Image Selection:** Use `alpine/k8s:1.28.13` (not stedolan/jq - image pull issues)
9. **readdir Implementation:** Deterministic script, not agent query
10. **Execution Modes:** Three modes (sequential/parallel/fake) via workflow.parameters.execution-mode

---

## Next Steps for Learning

### Pending Investigations
1. **Other Flow Types:** Analyze more complex flows with branching logic
2. **Custom Tools:** How to migrate custom LegacyX tool implementations
3. **Memory/State:** How ARK handles state between workflow runs
4. **Evaluation:** Migration of LegacyX evaluation framework
5. **Observability:** ARK equivalents for LegacyX monitoring

### Pending Transformer Migrations
- `parse_json`
- `concat_files`
- `extract_variables`
- Any custom transformers in `.lxtf` bundles

### Questions to Resolve
- How to handle LegacyX sessions in ARK?
- Best practices for large-scale parallel execution?
- ARK equivalent for LegacyX group composition?
- How to version workflows and maintain compatibility?

---

## Reference Locations

### Source Materials
- **LegacyX Demo:** `/Users/Antonio_Attanasio/legacyx/legacyx-demo/demos/kyc-onboarding/3.45.0/`
- **LegacyX Docs:** `/Users/Antonio_Attanasio/legacyx/qb-fm-labs-legacyx/docs/`
- **LegacyX Built-ins:** `/Users/Antonio_Attanasio/legacyx/qb-fm-labs-legacyx/docs/guide/sections/Builtins.md`

### ARK Resources
- **ARK Repo:** `/Users/Antonio_Attanasio/ark/agents-at-scale-ark/`
- **ARK CRD Schemas:** `/Users/Antonio_Attanasio/ark/agents-at-scale-ark/ark/config/crd/bases/`
- **UBO Resolver (Current):** `/Users/Antonio_Attanasio/ark/ubo-resolver/`
- **ARK Marketplace Examples:** `/Users/Antonio_Attanasio/aas/marketplace/agents-at-scale-marketplace/demos/`
- **KYC Demo Bundle:** `/Users/Antonio_Attanasio/aas/marketplace/agents-at-scale-marketplace/demos/kyc-demo-bundle/`

### Key Files
- **Working Example Workflow:** `/demos/kyc-demo-bundle/examples/kyc-onboarding-template.yaml`
- **Available Agents:** `/Users/Antonio_Attanasio/ark/ubo-resolver/agents/`
- **Available Teams:** `/Users/Antonio_Attanasio/ark/ubo-resolver/teams/`
- **Migration Summary:** `/Users/Antonio_Attanasio/ark/ubo-resolver/docs/TRANSLATION_SUMMARY.md`

---

## Critical Operational Notes

### AI Gateway API Key Management

⚠️ **IMPORTANT:** The OpenAI AI Gateway API key must be updated daily.

**Issue:** Queries fail with `403 Forbidden` error when the API key expires:
```
agent default/rag-agent execution failed: POST "https://openai.us.prod.ai-gateway.quantumblack.com/...": 403 Forbidden
```

**Solution:** Update the API key in the environment configuration before running workflows.

**Impact:** All agent/team queries will fail without valid authentication. This manifests as workflow steps completing successfully but producing no output files.

### Large File Access via Minikube Mount

For files larger than 1MB (filesystem MCP limit), use the minikube mount mechanism:

**Setup:**
```bash
# Running minikube mount (keep this process alive)
minikube mount /Users/Antonio_Attanasio/ark/feat-kyc/ubo-resolver/output:/mnt/output
```

**File Placement:**
- Local host path: `/Users/Antonio_Attanasio/ark/feat-kyc/ubo-resolver/output/`
- Accessible in pods at: `/mnt/output/`
- Argo script containers: `/mainctrfs/mnt/output/` (with prefix)

**Usage in Workflows:**
```yaml
# For PDF files (e.g., 12MB annual reports)
parameters:
  - name: document-file
    value: "/mnt/output/data/pdfs/abf-annual-report-2024.pdf"

# Volume mount in workflow
volumes:
  - name: mcp-filesystem-volume
    hostPath:
      path: /mnt/output
      type: DirectoryOrCreate

# In script templates
script:
  volumeMounts:
    - name: mcp-filesystem-volume
      mountPath: /mnt/output
```

**MCP Servers with Shared Storage:**

Update MCP server deployments to mount the shared volume:
```yaml
# ubo-pdf-tools deployment example
volumeMounts:
  - name: shared-pdfs
    mountPath: /mnt/output
    readOnly: true  # Read-only for MCP servers
volumes:
  - name: shared-pdfs
    hostPath:
      path: /mnt/output
      type: DirectoryOrCreate
```

**Two-Project Structure:**
- Main repository: `/Users/Antonio_Attanasio/ark/ubo-resolver/` (development)
- Mounted repository: `/Users/Antonio_Attanasio/ark/feat-kyc/ubo-resolver/` (runtime data)
- Copy large files to the mounted location for pod access

### Transformer Script Path Handling

**Argo Volume Mount Prefix:** Script containers add `/mainctrfs` prefix to volume mounts.

**Best Practice:** Check both paths in scripts:
```bash
# Script should handle both cases
BASE_DIR="${1:-/mnt/output/source_code_files}"

# Check if running in Argo wrapped container
if [ -d "/mainctrfs$BASE_DIR" ]; then
    BASE_DIR="/mainctrfs$BASE_DIR"
fi

# Now use $BASE_DIR for file operations
find "$BASE_DIR" -type f -name "*.json"
```

### Configuration Management with envsubst

**Pattern:** MCP server configurations use `$VARIABLE` syntax (not `${VARIABLE}`) for environment variables from `.env`.

**Critical:** Variables must be **exported** for envsubst to work:
```bash
# Load .env, export variables, and apply with substitution
source .env
export OPENAI_BASE_URL ANTHROPIC_BASE_URL UBO_LLM_DEFAULT_PROVIDER UBO_LLM_DEFAULT_MODEL
kubectl delete configmap ubo-pdf-tools-config  # Delete first if it exists
cd mcp-servers/ubo-pdf-tools
envsubst < k8s-direct.yaml | kubectl apply -f -
```

**Why export is required:** `envsubst` runs in a subshell and can only access exported environment variables. Simply sourcing `.env` sets variables in the current shell but doesn't export them.

**Variables from .env:**
- `OPENAI_BASE_URL` - OpenAI AI Gateway endpoint
- `ANTHROPIC_BASE_URL` - Anthropic AI Gateway endpoint  
- `UBO_LLM_DEFAULT_PROVIDER` - Default provider ("openai" or "anthropic")
- `UBO_LLM_DEFAULT_MODEL` - Default model (e.g., "gpt-4.1")
- `DAILY_API_TOKEN` - AI Gateway JWT (rotates daily)

**API Key Management:**

API keys stored in Kubernetes Secret `aigw-secret`:
```bash
# Update secret with fresh token from .env
source .env
kubectl create secret generic aigw-secret \
  --from-literal=api-key="$DAILY_API_TOKEN" \
  --from-literal=jwt-token="$DAILY_API_TOKEN" \
  --from-literal=token="$DAILY_API_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

**Daily Update Workflow:**
1. Update `DAILY_API_TOKEN` in `.env` with fresh JWT from AI Gateway
2. Run `./scripts/sync-env.sh` to sync everything

**Quick Sync (Recommended):**
```bash
# Edit .env with fresh token, then:
./scripts/sync-env.sh
```

**Manual Alternative:**
```bash
source .env
export OPENAI_BASE_URL ANTHROPIC_BASE_URL UBO_LLM_DEFAULT_PROVIDER UBO_LLM_DEFAULT_MODEL
kubectl create secret generic aigw-secret --from-literal=api-key="$DAILY_API_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
kubectl delete configmap ubo-pdf-tools-config 2>/dev/null || true
cd mcp-servers/ubo-pdf-tools && envsubst < k8s-direct.yaml | kubectl apply -f -
kubectl rollout restart deployment/ubo-pdf-tools
```

**Scripts:**
- `scripts/sync-env.sh` - **Main sync script** - Updates everything from .env
- `scripts/start.sh` - Uses envsubst when deploying MCP servers
- `scripts/update-api-key.sh` - Updates both secret and configs

---

## Instructions for Claude

When helping with LegacyX to ARK migration:

1. **Always check this file first** for established patterns and conventions
2. **Update this file** whenever you learn something new about the migration
3. **Follow the conventions** - don't invent new patterns unless existing ones don't work
4. **Reuse agents** whenever possible (check confidence levels)
5. **Test incrementally** - sequential mode first, then parallel
6. **Document mappings** - add new transformer/group mappings to tables above
7. **Verify resources** - check agent/team/tool availability before using
8. **Handle errors properly** - always check Query phase and capture errors
9. **Ask for clarification** when encountering unknown LegacyX constructs
10. **Keep user informed** - explain what you're doing and why

### When Analyzing a New Flow
1. Read the flow YAML completely
2. List all stages with types (transformer/group)
3. Check if groups/agents exist in ARK
4. Propose migration strategy before implementing
5. Highlight any uncertainties or risks

### When User Says "Something New"
1. Capture the information accurately
2. Categorize it (mapping, convention, best practice, etc.)
3. Add to appropriate section in this file
4. Confirm update with user

---

**Remember:** This is a living document. Update it every time you learn something new about the migration process.
