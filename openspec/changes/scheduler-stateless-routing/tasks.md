## 1. Local Cache

- [ ] 1.1 Implement `SandboxCache` class with TTL-based expiry (~5s): `get(cid) -> SandboxInfo | None`, `put(cid, info)`, `evict(cid)`, `warm(items)`
- [ ] 1.2 Unit tests for cache TTL expiry, eviction, and warm loading

## 2. K8s-Backed SandboxManager

- [ ] 2.1 Replace `_routing_table` dict with K8s API GET by deterministic claim name: cache check → GET claim → resolve sandbox FQDN from status
- [ ] 2.2 Replace `asyncio.Lock` with K8s create-conflict: CREATE claim, on 409 Conflict do GET and proceed with existing claim
- [ ] 2.3 Add `last-activity` annotation PATCH on each proxied request: `ark.mckinsey.com/last-activity` with ISO 8601 timestamp
- [ ] 2.4 Update `rebuild_map` to warm the local cache on startup instead of populating an authoritative routing table
- [ ] 2.5 Remove `_routing_table`, `_locks`, `_global_lock` fields from `SandboxManager`
- [ ] 2.6 Remove `add_alias` method from `SandboxManager`
- [ ] 2.7 Remove `touch` method (replaced by annotation PATCH inside `ensure_sandbox`)

## 3. Reaper Update

- [ ] 3.1 Update reaper to read `ark.mckinsey.com/last-activity` annotation from claims instead of in-memory `last_activity`
- [ ] 3.2 Handle missing annotation (claim created before this change) by treating it as expired or using claim creation timestamp
- [ ] 3.3 Make DELETE idempotent — treat 404 as success
- [ ] 3.4 Evict cache entry when reaping a session

## 4. Proxy Simplification

- [ ] 4.1 Remove `extract_response_context_id` function from `proxy.py`
- [ ] 4.2 Remove alias registration logic from the proxy handler (the `resp_ctx` / `add_alias` block)
- [ ] 4.3 Remove `touch()` call from proxy handler (last-activity is now handled by annotation PATCH in SandboxManager)

## 5. RBAC Update

- [ ] 5.1 Add `patch` verb to `sandboxclaims` in `scheduler-rbac.yaml` Role (needed for annotation updates)

## 6. Tests

- [ ] 6.1 Unit tests for K8s-backed `ensure_sandbox`: cache hit, cache miss with existing claim, new claim creation, 409 conflict handling
- [ ] 6.2 Unit tests for last-activity annotation PATCH
- [ ] 6.3 Unit tests for reaper with annotation-based TTL checking
- [ ] 6.4 Unit tests for startup cache warming
- [ ] 6.5 Update integration test to verify end-to-end flow with mocked K8s API instead of in-memory dict
- [ ] 6.6 Update `test_context_id.py` to remove alias-related tests
