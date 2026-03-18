## Why

The executor currently requires callers to pass the full conversation history with every request. A separate branch is introducing a `conversationId` field on `ExecutionEngineRequest` and removing the `history` list. The executor needs to manage conversation history internally using the `conversationId` to look up and persist messages across turns.

## What Changes

- **BREAKING**: Remove consumption of `request.history` — history is no longer supplied by the caller.
- Add `conversationId`-keyed in-memory conversation history using LangChain's native `ChatMessageHistory`.
- System prompt is prepended on first turn (when no history exists for a given `conversationId`).
- RAG-augmented messages are stored as-is in the history (no clean/augmented separation).
- Response messages are automatically appended to the conversation history after each turn.

## Capabilities

### New Capabilities
- `conversation-memory`: Server-side conversation history management keyed by `conversationId`, using LangChain's `ChatMessageHistory` for in-memory storage.

### Modified Capabilities

## Impact

- **Code**: `LangChainExecutor` in `executor.py` — replaces the history conversion block (lines 51-74) with history store lookup and management.
- **APIs**: `ExecutionEngineRequest` contract changes (done on separate branch) — `history` removed, `conversationId` added.
- **Dependencies**: No new dependencies. `ChatMessageHistory` is in `langchain_core.chat_history`, already available.
- **State**: Executor becomes stateful per-pod. History is lost on pod restart (acceptable for in-memory approach).
