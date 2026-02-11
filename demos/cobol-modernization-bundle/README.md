# COBOL Modernization Bundle

COBOL modernization demo with agents for reverse engineering, pseudocode generation, Python conversion, and documentation.

## What's Included

This bundle deploys **6 AI agents** that mirror the LegacyX Groups:

| ARK Agent | LegacyX Group | Description |
|-----------|---------------|-------------|
| `audio-transcriber` | Audio Transcription And Documentation | Transcribes audio files with speaker identification |
| `cobol-code-documenter` | Cobol Code Documentation | Creates detailed code spec documentation |
| `cobol-codebase-summarizer` | Cobol Codebase Summary | Generates codebase overview and interconnections |
| `cobol-pseudocode-documenter` | Cobol Pseudocode Documentation | Converts COBOL to language-agnostic pseudocode |
| `diagram-creator` | Diagram Creation | Generates PlantUML C4 architecture diagrams |
| `pseudo-python-modernizer` | Pseudo Python Modernizer | Converts pseudocode to Python/PySpark |

Plus supporting infrastructure:
- `speech-mcp-server` for local audio transcription via Whisper
- `file-gateway` MCP server for file operations (read/write/list)
- Argo Workflow RBAC for orchestration

## Prerequisites

- ARK cluster with `default` Model configured (Azure OpenAI)
- Argo Workflows installed
- `file-gateway` service (installed as dependency)
- Docker (to build the speech-mcp-server image)
- `kubectl` and `helm` CLI tools

## Quick Start

```bash
# Build, install, upload data, and run the workflow
make build && make install-with-argo && make upload-data && make cobol-demo
```

### Step by step

```bash
# 1. Build the speech-mcp-server Docker image
make build

# 2. Install the bundle (agents + file-gateway + speech-mcp + WorkflowTemplate)
make install-with-argo

# Upload sample COBOL files
make upload-data

# 4. Run the COBOL modernization workflow
make cobol-demo
```

## Sample Data

Sample COBOL files are included in `examples/data/cobol-source/`:
- 11 COBOL files from CardDemo application
- 1 audio file (interview recording)

## Output Artifacts

The workflow generates:
1. **Pseudocode Documentation** - Language-agnostic logic descriptions
2. **Audio Transcription** - Structured interview notes
3. **Architecture Diagrams** - PlantUML C4 model diagrams
4. **Python Code** - PySpark modules

## Agents

### audio-transcriber
Transcribes audio files with speaker identification. Creates structured markdown with:
- Overview
- Modernisation Plan
- Terminology and Context
- Potential Gaps
- Original Interview

### cobol-code-documenter
Creates comprehensive code documentation including:
- Business Documentation (overview, requirements, rules)
- Input/Output files grid
- Technical Documentation (paragraphs, logic rules, variable sources)

### cobol-codebase-summarizer
Generates codebase-wide documentation:
- Overview (purpose, architecture, folder structure)
- File Descriptions (categorisation, individual descriptions)
- Interconnections (call tree, dependency graph, data flow)
- Functions and Procedures (key functions, implementation details)
- Inputs and Outputs (files, data tables)

### cobol-pseudocode-documenter
Converts COBOL to pseudocode documentation:
- Business Overview
- Inputs and Outputs
- Pseudo-code (plain English, no COBOL terms)

### diagram-creator
Generates PlantUML diagrams:
- C4 Model architecture
- Hexagonal architecture patterns
- Target state focus

### pseudo-python-modernizer
Converts pseudocode to Python/PySpark:
- Idiomatic Python code
- PySpark for data processing
- Type hints and docstrings
- No SparkSession initialization

## Configuration

Override values in `values.yaml`:

```yaml
# Use a different model
modelRef:
  name: my-custom-model

# Disable specific agents
agents:
  audioTranscriber:
    enabled: false

# Change Whisper model (tiny, base, small, medium, large)
speechMcp:
  whisperModel: "small"
```

## Troubleshooting

**Agent not responding:**
```bash
kubectl get agent -n default
kubectl describe agent cobol-pseudocode-documenter -n default
```

**Audio transcription failing:**
```bash
kubectl logs deploy/speech-mcp -n default
```

**File operations failing:**
```bash
kubectl get mcpserver -n default
kubectl logs -l app=file-gateway -n default
```

**Workflow errors:**
```bash
argo list -n default
argo logs <workflow-name> -n default
```