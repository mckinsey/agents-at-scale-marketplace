## Context

The ark-sdk `ExecutorApp` injects a `BrokerClient` into `BaseExecutor` before calling `execute_agent()`. Executors opt in to real-time streaming by calling `await self.stream_chunk(token)` as content is generated. If no calls are made, `ExecutorApp` falls back to a single chunk at the end (Phase 1 behaviour). Each marketplace executor has its own streaming loop that needs a one-line integration.

## Goals / Non-Goals

**Goals:**
- Token-by-token streaming to the broker for all three marketplace executors
- Minimal, localised change per executor — one call per token in the existing streaming loop
- No change to `execute_agent()` return type or caller interface

**Non-Goals:**
- Changes to the broker client or chunk format (owned by ark-sdk)
- Streaming support for non-streaming model configurations
- LangChain executors that don't use streaming callbacks

## Decisions

### Decision: Call `stream_chunk()` inside existing streaming loops

Each executor already has a streaming path (OpenAI stream events, Anthropic stream events, LangChain callbacks). The integration is a single `await self.stream_chunk(token)` call at the point each token is available. No restructuring of executor logic needed.

### Decision: Accumulate full response independently of streaming

Executors already accumulate the full response to return from `execute_agent()`. The `stream_chunk()` call is additive — it does not replace accumulation. This ensures the A2A response and `Query.status.response` remain correct regardless of broker availability.

## Risks / Trade-offs

- **Requires ark-sdk Phase 2**: Executors calling `stream_chunk()` on an older SDK version will get an `AttributeError`. Mitigation: pin ark-sdk version in each executor's `pyproject.toml` and release together.
- **Double chunk if Phase 1 fallback triggers**: If `stream_chunk()` is called but `complete()` is not properly signalled, the broker may receive both streamed chunks and a final single chunk. Mitigation: ark-sdk handles this — if any `stream_chunk()` calls were made, the single-chunk fallback is skipped.

## Open Questions

- Should executors guard `stream_chunk()` with `hasattr` for backward compatibility with older SDK versions? (Defer to implementation — depends on release coordination.)
