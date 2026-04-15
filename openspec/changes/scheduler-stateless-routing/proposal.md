## Why

The scheduler stores all conversation-to-sandbox routing state in memory. This makes it a single point of failure — a pod restart loses alias mappings and resets idle TTLs, and running multiple replicas causes duplicate sandbox creation because each replica has its own independent routing table. Moving to Kubernetes-native state eliminates these issues and makes the scheduler horizontally scalable.

## What Changes

- Replace the in-memory routing table (`dict[str, SandboxInfo]`) with K8s API lookups on `SandboxClaim` resources using deterministic claim names
- Replace per-conversation `asyncio.Lock` with K8s create-conflict semantics (409 Conflict = another replica won the race)
- Store `last-activity` as an annotation on `SandboxClaim` instead of an in-memory float, enabling correct idle TTL reaping across restarts
- Add a short-lived local cache (~5s TTL) as a pure performance optimization — cache misses fall through to a single K8s GET by name
- Remove the alias mechanism entirely — the round-trip flow (scheduler injects contextId → executor echoes it → controller writes it to next query) means the same ID is always used
- Enable multiple scheduler replicas with shared-nothing architecture — each runs its own reaper independently (DELETE is idempotent)

## Capabilities

### New Capabilities

_(none — this refactors the internals of existing capabilities)_

### Modified Capabilities

- `sandbox-session-management`: Routing table, locking, and last-activity tracking move from in-memory to K8s-native. Alias mechanism removed. Local cache added as performance optimization. Multi-replica support.
- `scheduler-a2a-proxy`: Proxy interacts with the new K8s-backed SandboxManager instead of the in-memory dict. Response alias registration removed.

## Impact

- **Code**: `sandbox_manager.py` rewritten — `_routing_table`, `_locks`, `add_alias` replaced with K8s API calls + local cache. `proxy.py` simplified — alias registration removed.
- **K8s API load**: One GET per cache miss per request (~5s cache TTL), one PATCH per request for last-activity annotation, one LIST per reaper cycle per replica (every 30s).
- **RBAC**: Scheduler Role needs PATCH verb on `sandboxclaims` (currently only has create/delete/get/list/watch).
- **Tests**: Unit tests updated to mock K8s API calls instead of in-memory dict operations.
- **No changes**: to Helm chart values, CRD schemas, A2A protocol, or executor code.
