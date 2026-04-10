## Context

The scheduler currently stores all routing state in an in-memory `dict[str, SandboxInfo]`. This was the right starting point — simple, fast, correct for single-replica. But it prevents horizontal scaling and causes state loss on restart (alias mappings lost, idle TTLs reset).

The `SandboxClaim` custom resource already exists per conversation and carries the conversation-to-sandbox mapping via labels and status fields. It's 90% of a state store already. The gap is: last-activity tracking, and the code treats the local dict as authoritative instead of the claims.

## Goals / Non-Goals

**Goals:**
- Scheduler works correctly with multiple replicas (shared-nothing)
- Restart preserves all routing state including idle TTL timestamps
- No duplicate sandbox creation for the same conversation
- Minimal K8s API overhead on the hot path

**Non-Goals:**
- Leader election for the reaper (redundant LIST+DELETE across replicas is acceptable)
- Debouncing last-activity PATCH frequency (current turn-level frequency is fine; optimize later if streaming is added)
- Custom CRDs or external state stores (Redis, etcd directly, etc.)

## Decisions

### 1. SandboxClaim as single source of truth

**Decision**: The `SandboxClaim` custom resource is the authoritative state store. The in-memory routing table, per-conversation locks, and alias mechanism are removed.

**Alternatives considered**:
- *Shared Redis/memcached*: Adds an infrastructure dependency for what is fundamentally K8s-native state. The SandboxClaim already exists per conversation.
- *ConfigMap as state store*: Works but abuses the resource type. Claims are the natural fit — they already carry the sandbox mapping.

**Rationale**: The claim already stores conversation ID (label), sandbox name (status), and managed-by ownership (label). Adding a `last-activity` annotation completes the picture. No new resources, no new dependencies.

### 2. Deterministic claim name for O(1) lookup

**Decision**: Given a `conversationId`, derive the claim name deterministically: `sched-{short}-{hash}`. Any replica can compute the same name and do a direct `GET` by name instead of a label-selector LIST.

**Rationale**: GET by name is O(1) in the K8s API. Label-selector LIST scans all claims in the namespace. The current `_claim_name()` function is already deterministic — no change needed to the naming scheme.

### 3. K8s create-conflict as distributed lock

**Decision**: Replace `asyncio.Lock` per conversation with K8s resource creation semantics. Two replicas racing to create the same claim: one gets 201 Created, the other gets 409 Conflict. The loser does a GET and proceeds with the existing claim.

**Alternatives considered**:
- *Distributed lock via lease/configmap*: Adds complexity. The create-conflict pattern is simpler and handles the only race that matters (first-message sandbox creation).
- *Optimistic concurrency on annotations*: The `resourceVersion` field provides this for annotation updates, but we don't need it — a stale last-activity annotation just means a session lives slightly longer than configured, which is harmless.

**Rationale**: The only operation that needs mutual exclusion is claim creation. K8s already provides atomic creation with conflict detection.

### 4. Last-activity as annotation on the claim

**Decision**: Store `last-activity` as an ISO 8601 timestamp annotation (`ark.mckinsey.com/last-activity`) on the SandboxClaim. PATCH on each proxied request. The reaper reads this annotation when deciding whether to delete.

**Alternatives considered**:
- *Batch timestamps in a ConfigMap*: One object instead of N annotations, but adds a separate resource and requires list-then-patch coordination.
- *In-memory with periodic sync*: Keeps the fast path but reintroduces the restart problem for timestamps.

**Rationale**: One PATCH per A2A turn (every 10-60 seconds) is negligible K8s API load. The timestamp survives restarts. Any replica can read and act on it.

### 5. Local cache as pure performance optimization

**Decision**: Keep a short-lived local cache (`dict[str, SandboxInfo]` with ~5s TTL). Cache hits skip the K8s API entirely. Cache misses fall through to a single GET. The cache is not authoritative — evicting it entirely is always safe.

**Rationale**: Avoids a K8s API call on every request for active conversations. The TTL is short enough that a reaped sandbox is discovered within one missed request, triggering the existing recovery path (create new sandbox). For conversations with multiple rapid interactions, the cache absorbs all but the first lookup.

### 6. Remove alias mechanism

**Decision**: The `add_alias` method and response `contextId` extraction are removed. The round-trip flow already ensures continuity: scheduler injects `contextId` → executor echoes it → controller writes it to `status.conversationId` → dashboard uses it for the next query. The same ID always arrives.

**Rationale**: The alias was needed because the first message had no `contextId` and the executor might choose a different one. But the executor echoes the incoming `contextId` (confirmed in `executor_app.py:224`). The controller writes the echoed value to `status.conversationId`. Subsequent queries arrive with the same ID. No divergence.

### 7. Redundant reaper across replicas

**Decision**: Every replica runs its own reaper independently. Each reaper does `LIST claims → check annotation → DELETE expired`. Multiple replicas may delete the same claim — the second DELETE gets 404, which is harmless.

**Alternatives considered**:
- *Leader election*: One replica runs the reaper. Reduces LIST calls from N to 1 per cycle. Adds leader election machinery (Lease resource, coordination logic).

**Rationale**: For a typical deployment (2-3 replicas, 30s reaper interval), the extra LIST calls are negligible. Leader election adds complexity disproportionate to the benefit.

## Risks / Trade-offs

**[K8s API latency on cache miss]** → A GET by name is ~5-10ms within the cluster. For conversations with 10-60 second turns, this is invisible. If turn frequency increases (e.g., streaming), the cache absorbs it.

**[Stale cache routes to reaped sandbox]** → A replica's cache may point to a sandbox that another replica just reaped. The request fails, triggers recovery (new sandbox creation). This adds one-time latency for that request. Acceptable — the window is ≤5 seconds.

**[PATCH storm under high concurrency]** → 100 concurrent conversations = 100 annotation PATCHes per turn cycle. K8s API servers handle this easily. If it ever becomes a concern, debounce by only patching if the annotation is older than N seconds.

**[Reaper LIST across replicas]** → 3 replicas × 1 LIST per 30s = 6 LIST calls/minute. Trivial. The claims have the managed-by label, so the query is indexed.
