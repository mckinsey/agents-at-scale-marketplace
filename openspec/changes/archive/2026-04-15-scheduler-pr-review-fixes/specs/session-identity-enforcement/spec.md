## session-identity-enforcement

The scheduler enforces that all conversation IDs are valid UUID4 strings. This is the single enforcement point — everything downstream assumes clean UUIDs.

### Requirements

- [ ] `extract_context_id` validates incoming contextId as UUID4 using `uuid.UUID(value, version=4)`
- [ ] Missing or empty contextId: generate UUID4, inject into A2A body, return `is_new=True`
- [ ] Valid UUID4 contextId: pass through unchanged, return `is_new=False`
- [ ] Non-UUID4 contextId: return a JSON-RPC error response with HTTP 400 and message "contextId must be a valid UUID4 or omitted for auto-generation"
- [ ] The function signature changes to return a 3-tuple: `(context_id, body, is_new)`
- [ ] `is_new` is used by the proxy to decide between `create_sandbox` and `get_sandbox`

### Behavior Matrix

| Input contextId | Action | is_new | Response |
|----------------|--------|--------|----------|
| Missing/empty | Generate UUID4, inject | True | Proceed |
| Valid UUID4 | Pass through | False | Proceed |
| Non-UUID4 string | Reject | N/A | 400 error |

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "<from request>",
  "error": {
    "code": -32602,
    "message": "Invalid contextId: must be a valid UUID4 or omitted for auto-generation"
  }
}
```

Uses JSON-RPC error code -32602 (Invalid params) since contextId is a parameter of the A2A message.
