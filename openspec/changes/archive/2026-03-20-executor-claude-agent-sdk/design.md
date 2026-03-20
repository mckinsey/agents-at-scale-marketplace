## Context

The marketplace has one executor (LangChain) that wraps multiple LLM providers behind LangChain abstractions. For agents targeting Claude directly, this adds unnecessary indirection and prevents access to Claude Agent SDK's built-in tools (filesystem operations, shell commands). The langchain executor's patterns — BaseExecutor, ExecutorApp, Helm chart structure, CI/CD matrix, marketplace.json — are well-established and serve as the template for this new executor.

The ark repo establishes the `otel-environment-variables` secret pattern: a K8s Secret with `OTEL_EXPORTER_OTLP_ENDPOINT` and optional `OTEL_EXPORTER_OTLP_HEADERS`, loaded via `envFrom` with `optional: true`. This executor follows that same pattern.

## Goals / Non-Goals

**Goals:**
- Provide a native Claude executor with built-in tool access (Read, Write, Edit, Bash, Grep, Glob)
- Support multi-turn conversations via `ClaudeSDKClient` with `resume`, keyed by `conversationId`
- Scope each session to its own filesystem directory on a PVC
- Enable OTEL tracing conditionally via the established `otel-environment-variables` secret pattern
- Follow all existing marketplace conventions (Helm chart, CI/CD, marketplace.json, docs)

**Non-Goals:**
- Multi-model support (this executor is Anthropic-only; use langchain executor for other providers)
- Custom tool definitions beyond the SDK's built-ins (can be added later via MCP servers)
- Streaming responses to the caller (collect full response, return as single message)
- Session cleanup / garbage collection (future concern)
- Horizontal scaling with shared session state (single replica with PVC is sufficient for now)

## Decisions

### D1: ClaudeSDKClient over query()

**Choice**: Use `ClaudeSDKClient` with `resume` for multi-turn sessions.

**Alternatives considered**:
- `query()`: Simpler API but stateless — each call starts fresh with no session continuity. Would require manual conversation history management (re-injecting prior messages).
- `ClaudeSDKClient`: Supports `resume` with session ID, SDK handles session persistence on disk under `.claude/` in the working directory.

**Rationale**: Session continuity comes free via the SDK's own persistence. The `conversationId` from A2A requests maps naturally to a session directory, and `resume` picks up where it left off without manual history management.

### D2: Per-session filesystem directories on PVC

**Choice**: Each `conversationId` gets `/data/sessions/<conversationId>/` as the SDK's `cwd`. The PVC is mounted at `/data/sessions/`.

**Rationale**: The SDK's built-in tools (Read, Write, Bash, etc.) operate on the filesystem relative to `cwd`. Scoping each session to its own directory provides isolation between conversations and ensures the SDK's session state (stored in `.claude/`) persists across pod restarts.

### D3: openinference-instrumentation-claude-agent-sdk for OTEL

**Choice**: Use `openinference-instrumentation-claude-agent-sdk` from Arize for OTEL instrumentation.

**Alternatives considered**:
- `langsmith[claude-agent-sdk, otel]`: Requires LangSmith as intermediary, adds unnecessary dependency.
- `opentelemetry-instrumentation-claude-agent-sdk` (community): Less mature, smaller community.
- Manual instrumentation via PreToolUse/PostToolUse hooks: More work, less standardized.

**Rationale**: openinference supports both `query()` and `ClaudeSDKClient.receive_response()`, captures agent spans with tool call child spans, follows GenAI semantic conventions, and is maintained by Arize (Phoenix). It instruments `receive_response()` with one span per response turn, capturing input/output/metadata and tool spans via SDK hooks.

### D4: Environment variables for API key and model configuration

**Choice**: `ANTHROPIC_API_KEY` from a K8s secret (`anthropic-api-key`), `ANTHROPIC_MODEL` from deployment env with a sensible default.

**Rationale**: Follows the same pattern as the ark completions executor. No need to parse model type from the A2A request — this executor is always Anthropic. Keeps configuration simple and Kubernetes-native.

### D5: Conditional OTEL initialization

**Choice**: Only initialize TracerProvider and instrumentor when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

**Rationale**: Matches the ark pattern. The `otel-environment-variables` secret is `optional: true` in the deployment — if it doesn't exist, OTEL env vars are simply absent and tracing is a no-op. Zero overhead when disabled.

## Risks / Trade-offs

**[Single replica + PVC]** → Sessions are tied to one pod. Horizontal scaling would require shared storage or session affinity. Acceptable for initial release; document as known limitation.

**[SDK subprocess model]** → The Claude Agent SDK spawns a subprocess for tool execution. Resource limits in the Helm chart need to account for this. Mitigation: Set reasonable CPU/memory limits and document tuning guidance.

**[Session disk growth]** → Sessions accumulate on the PVC with no automatic cleanup. Mitigation: Document manual cleanup; defer automated GC to a future change.

**[SDK version coupling]** → The executor depends on `claude-agent-sdk` which is actively evolving. Mitigation: Pin version in `pyproject.toml`, test on upgrades.

**[Built-in tools security]** → Full tool access (including Bash) means an agent can execute arbitrary commands on the pod. Mitigation: Pod runs as non-root (UID 1001), security context drops capabilities, network policies can limit egress. Document that `allowed_tools`/`disallowed_tools` in ClaudeAgentOptions can restrict tool access per deployment.
