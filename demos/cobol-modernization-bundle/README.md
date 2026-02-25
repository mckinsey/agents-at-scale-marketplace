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
- Argo Workflow RBAC (ServiceAccount + Role + RoleBinding)
- Data seeder (Helm post-install hook that uploads sample files automatically)
- WorkflowTemplate for the full COBOL modernization pipeline

## Prerequisites

- **Model for agents:** A Model (e.g. named `default`) must exist in the namespace where you install the bundle. Agents use this Model to run, workflows will fail until it is present. Create the Model (e.g. via ARK Dashboard → Models or `ark models create default`) in the target namespace. 
- ARK cluster (Azure OpenAI or other provider)
- Argo Workflows installed
- `file-gateway` service (installed as dependency)
- Docker (to build the speech-mcp-server image)
- `kubectl` and `helm` CLI tools

## Local Development

You can install the bundle in **any namespace**. If you don't set `NAMESPACE`, it installs in **default**. Ensure the prerequisites are met.

```bash
cd agents-at-scale-marketplace/demos/cobol-modernization-bundle

# Install in default namespace (no NAMESPACE needed)
make build
make install-with-argo
make upload-data
make cobol-demo

# Or install in a specific namespace (create/copy Model there first if needed)
make install-with-argo NAMESPACE=cobol-demo
make upload-data NAMESPACE=cobol-demo
make cobol-demo NAMESPACE=cobol-demo

# View results (use the namespace you installed into)
kubectl get workflows -n default   # or -n cobol-demo

# Cleanup (use same NAMESPACE as install)
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
