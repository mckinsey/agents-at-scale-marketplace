## ADDED Requirements

### Requirement: Receive A2A requests as an ExecutionEngine
The scheduler SHALL expose an A2A-compatible HTTP endpoint and be registered as an `ExecutionEngine` CRD so the Ark controller can dispatch queries to it using the standard A2A protocol.

#### Scenario: Controller sends A2A message to scheduler
- **WHEN** the Ark controller dispatches a Query to an Agent whose `spec.executionEngine` references the scheduler's `ExecutionEngine`
- **THEN** the scheduler SHALL receive the A2A HTTP POST request on its registered endpoint

#### Scenario: Health check
- **WHEN** a GET request is made to `/health`
- **THEN** the scheduler SHALL respond with HTTP 200

### Requirement: Extract conversation ID from A2A message
The scheduler SHALL parse the incoming A2A JSON request body to extract the `context_id` field from the message for routing purposes. All other A2A content SHALL be treated as opaque.

#### Scenario: A2A message with context_id
- **WHEN** an A2A request arrives with `context_id` set to `conv-abc-123`
- **THEN** the scheduler SHALL extract `conv-abc-123` as the conversation ID for sandbox routing

#### Scenario: A2A message without context_id
- **WHEN** an A2A request arrives with no `context_id` or an empty `context_id`
- **THEN** the scheduler SHALL generate a unique conversation ID for this request and use it for sandbox creation

### Requirement: Proxy A2A request to sandbox
The scheduler SHALL forward the complete A2A HTTP request (body, headers) to the target sandbox pod's A2A endpoint and relay the sandbox's HTTP response back to the Ark controller.

#### Scenario: Successful proxy round-trip
- **WHEN** a sandbox is resolved for a conversation and the A2A request is forwarded
- **THEN** the scheduler SHALL send the original HTTP body and headers (excluding `Host`) to `http://<sandbox-serviceFQDN>:8000/`, receive the sandbox's response, and return it to the controller with the same status code and headers

#### Scenario: Sandbox returns A2A error
- **WHEN** the sandbox executor returns an A2A error response (e.g., CRD resolution failure, Claude SDK error)
- **THEN** the scheduler SHALL relay the error response as-is to the controller without modification

### Requirement: Surface sandbox infrastructure errors
The scheduler SHALL return HTTP 502 with a descriptive error body when sandbox infrastructure failures prevent request proxying. These errors SHALL be distinct from executor-level A2A errors.

#### Scenario: Sandbox pod unreachable during proxy
- **WHEN** the scheduler attempts to forward a request to a sandbox but the HTTP connection fails
- **THEN** the scheduler SHALL return HTTP 502 to the controller with a body describing the connection failure

#### Scenario: Sandbox creation timeout during first message
- **WHEN** sandbox creation or readiness exceeds the configured timeout during the first message of a conversation
- **THEN** the scheduler SHALL return HTTP 502 to the controller with a body describing the timeout
