# executor-openai-responses

An [Ark](https://github.com/mckinsey/agents-at-scale-ark) executor that routes agent queries to the [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses).

## Why Responses API?

| Feature | Completions executor | This executor |
|---|---|---|
| Built-in tools (web search, file search, …) | ✗ | ✓ |
| Multi-turn efficiency | Resends full history | `previous_response_id` |
| Structured output | Via prompt | Native JSON schema |
| Streaming events | Chunk-level | Tool call + text deltas |

## Configuration

### Model CRD

The agent's `modelRef` must point to a Model CR whose `config.openai` block contains an `apiKey`:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Model
metadata:
  name: gpt-4o
spec:
  provider: openai
  config:
    openai:
      apiKey: sk-...          # required
      baseUrl: https://...    # optional — override for proxies / Azure
```

### Built-in tools

Enable OpenAI server-side tools via Agent CR labels:

| Label | Tool |
|---|---|
| `ark.openai.tools/web-search-preview: "true"` | Web search |
| `ark.openai.tools/file-search: "true"` | File search |
| `ark.openai.tools/code-interpreter: "true"` | Code interpreter |
| `ark.openai.tools/computer-use-preview: "true"` | Computer use |

#### Web search user location

Pass location context for web search via Agent CR parameters:

```yaml
spec:
  parameters:
    - name: openai.web-search.country
      value: GB
    - name: openai.web-search.city
      value: London
    - name: openai.web-search.region
      value: London
```

### How `instructions` and `input` map to Agent CR fields

The Responses API separates static context from runtime content:

| Responses API field | Source | Example |
|---|---|---|
| `instructions` | `spec.prompt` on the Agent CR | `"You are an expert web search agent..."` |
| `input` | Query CR / runtime user message | `"ADAM GROOMING BN LTD"` |

The Agent CR holds the **static** configuration. The **runtime query** (what you'd type as a user) is submitted separately via a Query CR and arrives in the executor as `request.userInput.content`.

### Example: web search agent

**Agent CR** (static config — applied once):

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: website-search-agent
  labels:
    ark.openai.tools/web-search-preview: "true"
spec:
  modelRef:
    name: gpt-5-nano-2025-08-07
  executionEngineRef:
    name: executor-openai-responses
  prompt: |
    You are an expert web search agent located in UK.
    Your role is to find the link to the main website of a given company located in UK.
    Return only the link and nothing else. Do not write any comments or explanation.
  parameters:
    - name: openai.web-search.country
      value: GB
    - name: openai.web-search.city
      value: London
    - name: openai.web-search.region
      value: London
```

**Query CR** (runtime input — submitted per request):

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: find-adam-grooming
spec:
  agentRef:
    name: website-search-agent
  message: "ADAM GROOMING BN LTD"
```

This maps to the following Responses API call:

```python
client.responses.create(
    model="gpt-5-nano-2025-08-07",
    instructions="You are an expert web search agent located in UK...",
    input="ADAM GROOMING BN LTD",
    tools=[{
        "type": "web_search_preview",
        "user_location": {"type": "approximate", "country": "GB", "city": "London", "region": "London"},
    }],
)
# → https://adamgroomingatelier.com/
```

## Executor UI

This executor serves a built-in chat + file-upload UI at `GET /` on the pod, backed by:

- `POST /chat` — SSE stream of text deltas, with conversation threading via `previous_response_id` saved under `SESSIONS_DIR/<conversationId>/`.
- `POST /chat/reset` — drop the saved `previous_response_id` for a conversation.
- `/v1/files` (POST/GET/DELETE) — OpenAI-compatible Files API. Uploads here can be attached to queries via the `executor-openai-file-inputs.ark.mckinsey.com/file-ids` annotation — see the [`openai-file-inputs` executor](../openai-file-inputs/README.md) for the annotation cascade. The same annotation works whether the chat agent targets this executor or `openai-file-inputs`.

### Scoping uploads to an agent

All `/v1/files` endpoints accept `?agent=<namespace>/<name>` (or just `<name>`). When set:

- Credentials come from the named agent's `modelRef.config.openai.{apiKey,baseUrl}`, so uploads land in the same OpenAI project the agent's Responses calls use.
- `GET /v1/files` only returns files this agent uploaded (a per-agent index lives at `SESSIONS_DIR/file_index.json` on the executor's PVC).

Without `?agent=`, the executor falls back to the cluster-wide `OPENAI_API_KEY` env var and `GET /v1/files` returns every file that key can see.

| Env Var | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Cluster-wide fallback for Files API |
| `OPENAI_BASE_URL` | — | Optional override for the fallback |
| `FILE_PROVIDER` | `openai` | File backend (only `openai` today) |
| `SESSIONS_DIR` | `/data/sessions` | Persistence for response IDs and the per-agent file index |

## Deployment

```bash
# Install via Helm
helm install executor-openai-responses ./chart -n default

# Or use DevSpace for local development
devspace deploy
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run locally
uv run executor-openai-responses
```
