## Context

The LangChain executor currently receives the full conversation history as a `List[Message]` on every request. A separate branch changes the `ExecutionEngineRequest` contract to replace `history` with a `conversationId` string. The executor must now manage conversation state internally.

The executor runs as a stateless pod in Kubernetes. LangChain provides native `ChatMessageHistory` (in `langchain_core.chat_history`) for in-memory conversation storage.

## Goals / Non-Goals

**Goals:**
- Use LangChain's native `ChatMessageHistory` to store and retrieve conversation history by `conversationId`.
- Maintain current behavior: system prompt on first turn, RAG context injected into user messages, response appended to history.
- Keep the change minimal and contained to `executor.py`.

**Non-Goals:**
- Persistent/shared history backends (Redis, Postgres). In-memory only for now.
- Conversation eviction, TTL, or memory pressure management.
- Separating clean vs RAG-augmented messages in history.
- Multi-pod history sharing or sticky sessions.

## Decisions

### 1. In-memory dict on the executor instance
**Choice**: `self.history_store: Dict[str, ChatMessageHistory] = {}` on `LangChainExecutor`.

**Alternatives considered**:
- `RunnableWithMessageHistory` wrapper — adds indirection and changes the invocation pattern. Overkill when we just need a dict lookup and manual message appends.
- External store (Redis) — adds infrastructure dependency. Can be swapped in later since `ChatMessageHistory` and `RedisChatMessageHistory` share the same interface.

**Rationale**: Simplest approach. The dict lives on the instance like `self.vector_store` already does. Swapping to a persistent backend later is a one-line change in the factory function.

### 2. First-turn detection via empty history
**Choice**: If `conversationId` has no entry in the store, it's the first turn — create a new `ChatMessageHistory` and prepend the system prompt.

**Rationale**: Direct replacement for the current `if len(request.history) == 0` check. No additional signaling from the orchestrator needed.

### 3. Store RAG-augmented messages as-is
**Choice**: The user message stored in history includes the RAG context prefix when RAG is active.

**Rationale**: Avoids dual-message bookkeeping. Since history is in-memory and ephemeral, there's no downstream consumer that would need the clean version.

## Risks / Trade-offs

- **History lost on pod restart** → Acceptable for in-memory. The orchestrator can start a new conversation.
- **Unbounded memory growth** → Low risk given pod lifecycle. If it becomes a problem, add LRU eviction or a max-conversations cap later.
- **RAG context in history inflates token usage on subsequent turns** → The LLM sees prior RAG context in history. Acceptable trade-off for simplicity; could be revisited if token costs become a concern.
