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

## Local Development

```bash
# 3 simple steps:
cd agents-at-scale-marketplace/demos/cobol-modernization-bundle

make build                  # 1. Build the speech-mcp-server Docker image
make install-with-argo      # 2. Install everything
make upload-data            # 3. Upload example customer file
make cobol-demo               # 4. Run KYC workflow

# View results
kubectl get workflows -n default
# Access ARK Dashboard → Workflow Templates (template is visible)
# Access ARK Dashboard → Files section (download report)

# Cleanup
make uninstall
```

## Cloud Deployment

```bash
# Install the bundle
ark install marketplace/demos/cobol-modernization-bundle
```

**Upload input data (ARK Dashboard):**

1. Open **ARK Dashboard → Files**.
2. Create or use the folder `cobol-source/`.
3. Upload your COBOL files (`.cbl`) and the audio file (e.g. `carddemo-interview.m4a`).

**Run the workflow:**

- From **ARK Dashboard → Argo Workflows**, submit a new workflow that references the `cobol-modernization-template` WorkflowTemplate, or apply the example workflow manifest:
  - [cobol-modernization-from-template.yaml](https://github.com/mckinsey/agents-at-scale-marketplace/blob/main/demos/cobol-modernization-bundle/examples/cobol-modernization-from-template.yaml)
- Use parameters such as `cobol-source-dir=cobol-source`, `output-dir=output`, and `audio-file=cobol-source/carddemo-interview.m4a` to match your uploaded paths.
