## ADDED Requirements

### Requirement: Conditional OTEL initialization
The executor SHALL initialize OpenTelemetry tracing only when the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable is set. When not set, tracing SHALL be completely disabled with zero overhead.

#### Scenario: OTEL endpoint configured
- **WHEN** `OTEL_EXPORTER_OTLP_ENDPOINT` is set to a valid URL
- **THEN** the executor SHALL create a `TracerProvider` with an `OTLPSpanExporter` targeting that endpoint and instrument the Claude Agent SDK via `ClaudeAgentSDKInstrumentor().instrument()`

#### Scenario: OTEL endpoint not configured
- **WHEN** `OTEL_EXPORTER_OTLP_ENDPOINT` is not set
- **THEN** no `TracerProvider` SHALL be created and no instrumentation SHALL be applied

#### Scenario: OTEL headers configured
- **WHEN** `OTEL_EXPORTER_OTLP_HEADERS` is set alongside `OTEL_EXPORTER_OTLP_ENDPOINT`
- **THEN** the OTLP exporter SHALL include those headers in trace export requests (for authentication with backends like Langfuse, Phoenix, or Honeycomb)

### Requirement: otel-environment-variables secret pattern
The Helm chart deployment template SHALL load OTEL configuration from a K8s secret named `otel-environment-variables` via `envFrom` with `optional: true`, following the pattern established in the ark repository.

#### Scenario: Secret exists
- **WHEN** an `otel-environment-variables` secret exists in the namespace with `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`
- **THEN** those values SHALL be available as environment variables in the executor pod and tracing SHALL be active

#### Scenario: Secret does not exist
- **WHEN** no `otel-environment-variables` secret exists in the namespace
- **THEN** the executor SHALL start normally without tracing (the `optional: true` flag prevents pod startup failure)

### Requirement: Agent and tool span capture
When OTEL is enabled, the instrumentation SHALL capture agent spans for each `receive_response()` turn and child tool spans for each tool invocation via the SDK's PreToolUse/PostToolUse hooks.

#### Scenario: Multi-turn conversation with tool use
- **WHEN** OTEL is enabled and an agent uses the Read and Bash tools during a response
- **THEN** the trace SHALL contain an agent span with child tool spans for Read and Bash, including input/output metadata
