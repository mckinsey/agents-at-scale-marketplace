## MODIFIED Requirements

### Requirement: Extract conversation ID from A2A message
The scheduler SHALL parse the incoming A2A JSON-RPC request body to extract the `contextId` field from `params.message.contextId` for routing purposes. All other A2A content SHALL be treated as opaque. When `contextId` is missing, the scheduler SHALL generate one and inject it into the forwarded body.

#### Scenario: A2A message with contextId
- **WHEN** an A2A request arrives with `params.message.contextId` set to `conv-abc-123`
- **THEN** the scheduler SHALL extract `conv-abc-123` as the conversation ID for sandbox routing and forward the body unchanged

#### Scenario: A2A message without contextId
- **WHEN** an A2A request arrives with no `contextId` or an empty `contextId` in `params.message`
- **THEN** the scheduler SHALL generate a unique conversation ID, inject it as `contextId` into `params.message` in the forwarded body, and use it for sandbox creation

### Requirement: Proxy A2A request to sandbox
The scheduler SHALL forward the complete A2A HTTP request (body, headers) to the target sandbox pod's A2A endpoint and relay the sandbox's HTTP response back to the Ark controller. The `Host` and `Content-Length` headers SHALL be excluded from forwarding — the HTTP client SHALL recalculate `Content-Length` from the actual body.

#### Scenario: Successful proxy round-trip
- **WHEN** a sandbox is resolved for a conversation and the A2A request is forwarded
- **THEN** the scheduler SHALL send the HTTP body and headers (excluding `Host`, `Content-Length`, `Transfer-Encoding`) to `http://<sandbox-serviceFQDN>:8000/`, receive the sandbox's response, and return it to the controller with the same status code and headers

#### Scenario: Sandbox returns A2A error
- **WHEN** the sandbox executor returns an A2A error response (e.g., CRD resolution failure, Claude SDK error)
- **THEN** the scheduler SHALL relay the error response as-is to the controller without modification

## REMOVED Requirements

### Requirement: Register response contextId as routing alias
**Reason**: The alias mechanism is unnecessary. The executor echoes the incoming `contextId` in its response. The controller writes the echoed value to `status.conversationId`. Subsequent queries arrive with the same ID. No divergence occurs.
**Migration**: Remove `extract_response_context_id` and `add_alias` calls from the proxy handler.
