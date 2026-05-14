# OpenAI File Inputs Executor

OpenAI Responses API executor that attaches files to queries via the `input_file` content type. Reads OpenAI `file_id`s from a query annotation and passes them to the Responses API alongside the user text.

## Flow

1. A user uploads a file somewhere that hits the OpenAI Files API (e.g. the upload UI on [`executor-openai-responses`](../openai-responses/README.md), or OpenAI directly) → receives a `file_id`.
2. A Query CR carries those file IDs on the annotation `executor-openai-file-inputs.ark.mckinsey.com/file-ids` (JSON array of strings, e.g. `["file-abc","file-def"]`).
3. This executor reads the annotation via the cascade (Query > Agent > ExecutionEngine) and builds multimodal input:
   `[{type: "input_file", file_id: "..."}, {type: "input_text", text: "..."}]`.
4. Calls the OpenAI Responses API with streaming.

The annotation cascade matches the pattern used for `tools`, `reasoning`, and `output-schema` — Query overrides Agent overrides ExecutionEngine.

The same `file-ids` annotation is honoured by [`executor-openai-responses`](../openai-responses/README.md). Use that executor if you also want a built-in upload UI; use this one when you want a dedicated execution engine whose only behaviour is file-attached Responses calls.

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `SESSIONS_DIR` | `/data/sessions` | Per-conversation `previous_response_id` storage |

The OpenAI API key for the Responses call comes from the agent's Model CR — there is no executor-level key.

## Local Development

```bash
cd executors/openai-file-inputs
uv sync
uv run executor-openai-file-inputs
```

## Deployment

```bash
ark install marketplace/executor/openai-file-inputs
```
