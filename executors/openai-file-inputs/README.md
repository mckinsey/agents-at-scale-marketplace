# OpenAI File Inputs Executor

OpenAI Responses API executor with file attachment support. Exposes an OpenAI-compatible Files API (`/v1/files`) for uploading files and passes file IDs as `input_file` content parts to the Responses API.

## Flow

1. UI uploads file via `POST /v1/files` → receives OpenAI `file_id`
2. `file_id` sent with user message in `userInput.file_ids`
3. Executor builds multimodal input: `[{type: "input_file", file_id: "..."}, {type: "input_text", text: "..."}]`
4. Calls OpenAI Responses API with streaming

## File API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/files` | Upload file (multipart: `file` + `purpose`) |
| GET | `/v1/files` | List files |
| GET | `/v1/files/{file_id}` | Get file metadata |
| DELETE | `/v1/files/{file_id}` | Delete file |

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `OPENAI_API_KEY` | — | API key for Files API proxy |
| `SESSIONS_DIR` | `/data/sessions` | Session persistence directory |
| `MAX_TOOL_ITERATIONS` | `10` | Max function call loop iterations |

The model API key (for Responses API calls) comes from the Model CRD, same as other executors.

## Local Development

```bash
cd executors/openai-file-inputs
uv sync
OPENAI_API_KEY=sk-... uv run executor-openai-file-inputs
```

## Deployment

```bash
ark install marketplace/executor/openai-file-inputs
```
