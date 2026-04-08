## ADDED Requirements

### Requirement: Propagate OTEL trace context through proxy
The scheduler SHALL extract W3C TraceContext (`traceparent`) and Baggage headers from incoming A2A requests and include them in proxied requests to sandbox pods, maintaining trace continuity from the Ark controller through the scheduler to the executor.

#### Scenario: Trace context forwarded to sandbox
- **WHEN** an A2A request arrives with `traceparent` and `baggage` headers
- **THEN** the scheduler SHALL include these headers (updated with scheduler span context) in the proxied request to the sandbox pod

#### Scenario: No trace context in request
- **WHEN** an A2A request arrives without `traceparent` headers
- **THEN** the scheduler SHALL optionally create a new trace root (if OTEL is configured) or forward the request without trace headers

### Requirement: Scheduler span for request routing
The scheduler SHALL create an OTEL span named `scheduler.route` for each incoming A2A request. This span SHALL be a child of the incoming trace context and SHALL be the parent of all sandbox lifecycle and proxy spans.

#### Scenario: Returning conversation routed to existing sandbox
- **WHEN** an A2A request is routed to an existing sandbox
- **THEN** the `scheduler.route` span SHALL include attributes `sandbox.conversation_id`, `sandbox.name`, and `sandbox.is_new: false`, and SHALL contain a child span `scheduler.proxy.forward`

#### Scenario: New conversation with sandbox creation
- **WHEN** an A2A request triggers sandbox creation
- **THEN** the `scheduler.route` span SHALL include `sandbox.is_new: true` and SHALL contain child spans for `scheduler.sandbox.create`, `scheduler.sandbox.wait_ready`, and `scheduler.proxy.forward`

### Requirement: Sandbox lifecycle spans
The scheduler SHALL create OTEL spans for sandbox lifecycle operations: `scheduler.sandbox.create` (claim creation), `scheduler.sandbox.resolve_name` (sandbox name resolution from claim), and `scheduler.sandbox.wait_ready` (waiting for sandbox readiness).

#### Scenario: Sandbox creation with warm pool
- **WHEN** a sandbox is allocated from a warm pool
- **THEN** the `scheduler.sandbox.wait_ready` span SHALL have a short duration reflecting the pre-warmed state, and the `scheduler.sandbox.resolve_name` span SHALL include attribute `sandbox.warm_pool: true` if the sandbox name differs from the claim name

#### Scenario: Sandbox creation failure
- **WHEN** sandbox creation or readiness times out
- **THEN** the relevant span SHALL be marked with error status and include the error description

### Requirement: Proxy forwarding span
The scheduler SHALL create an OTEL span named `scheduler.proxy.forward` covering the HTTP round-trip to the sandbox pod. This span SHALL include the sandbox's service FQDN as an attribute.

#### Scenario: Successful proxy round-trip
- **WHEN** the A2A request is proxied to a sandbox and a response is received
- **THEN** the `scheduler.proxy.forward` span SHALL record the HTTP status code and duration

#### Scenario: Proxy connection failure
- **WHEN** the proxy request fails due to a connection error
- **THEN** the `scheduler.proxy.forward` span SHALL be marked with error status and include the connection error details
