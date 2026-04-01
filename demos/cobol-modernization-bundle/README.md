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
- **`file-gateway`** (installed as a **Helm dependency** )
- Argo Workflow RBAC (ServiceAccount + Role + RoleBinding)
- **Data seeder** (optional): Helm post-install hook uploads sample files; run `make build-data-seeder` before install for Option A
- **`make upload-data`** (Option B): manual upload via file-gateway-api
- WorkflowTemplate for the full COBOL modernization pipeline

## Prerequisites

- **Model for agents:** A Model (e.g. named `default`) must exist in the namespace where you install the bundle. Agents use this Model to run, workflows will fail until it is present. Create the Model (e.g. via ARK Dashboard → Models or `ark models create default`) in the target namespace. 
- ARK cluster (Azure OpenAI or other provider)
- Argo Workflows installed
- **File Gateway** is installed automatically with this bundle (Helm dependency); no separate install step.
- Docker (to build the speech-mcp-server and data-seeder images)
- `kubectl` and `helm` CLI tools

## Local Development

Install in any namespace (default if omitted). Prerequisites must be met. If file-gateway is already in the namespace (e.g. from the KYC demo), use `USE_EXISTING_FILE_GATEWAY=true` so the bundle skips installing it and uses the existing one.

**For a clean install** (recommended): run `make uninstall` first to remove any existing bundle and file-gateway; then run the steps below.

### Option A: Data seeder (automatic upload on install)

Build the data-seeder image, then build and install. A post-install hook runs the seeder and uploads sample COBOL/audio.

```bash
cd agents-at-scale-marketplace/demos/cobol-modernization-bundle
make uninstall
make build-data-seeder
make build
make install-with-argo
make cobol-demo
```

### Option B: Manual upload

Build and install with the data-seeder disabled, then run `make upload-data` to upload from `examples/data/cobol-source/`.

```bash
cd agents-at-scale-marketplace/demos/cobol-modernization-bundle
make uninstall
make build
make install-with-argo DATA_SEEDER_ENABLED=false
make upload-data
make cobol-demo
```

**Testing Option B after Option A:** Re-run install with the seeder disabled, then upload manually. Optionally delete the existing data-seeder Job first for a clean state:
```bash
make delete-data-seeder-job
make install-with-argo DATA_SEEDER_ENABLED=false
make upload-data
make cobol-demo
```

Use `NAMESPACE=<ns>` for install/upload/cobol-demo when using a non-default namespace. Cleanup: `make uninstall`.

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
