## MODIFIED Requirements

### Requirement: Create sandbox for new conversation
The scheduler SHALL create a `SandboxClaim` referencing the configured `SandboxTemplate` when an A2A request arrives with a `context_id` that has no existing sandbox mapping. The claim SHALL be labeled with `ark.mckinsey.com/conversation-id: <context_id>` and `ark.mckinsey.com/managed-by: claude-agent-sdk-scheduler`. The proxy layer SHALL signal Query provisioning status before sandbox creation begins and after the sandbox becomes ready.

#### Scenario: First message in a new conversation
- **WHEN** an A2A request arrives with `context_id` set to `conv-abc-123` and no sandbox exists for that conversation
- **THEN** the scheduler SHALL signal Query phase `provisioning`, create a `SandboxClaim` in the configured namespace referencing the configured `SandboxTemplate`, labeled with `ark.mckinsey.com/conversation-id: conv-abc-123`, wait for the sandbox to become Ready, resolve its service FQDN from the Sandbox status, signal Query phase `running`, and store the conversation-to-sandbox mapping

#### Scenario: Warm pool sandbox allocation
- **WHEN** a `SandboxWarmPool` exists with available pre-warmed pods and a new conversation arrives
- **THEN** the scheduler SHALL signal Query phase `provisioning`, create a `SandboxClaim`, and the agent-sandbox controller SHALL allocate a warm sandbox, resulting in faster readiness compared to cold creation, after which the scheduler SHALL signal Query phase `running`

#### Scenario: Sandbox creation failure
- **WHEN** the `SandboxClaim` creation fails (K8s API error, quota exceeded)
- **THEN** the scheduler SHALL return HTTP 502 to the Ark controller with a descriptive error body — the Query phase will be overwritten by the controller's error handling

#### Scenario: Sandbox readiness timeout
- **WHEN** a sandbox does not become Ready within the configured `sandboxReadyTimeout`
- **THEN** the scheduler SHALL delete the `SandboxClaim`, remove any partial mapping, and return HTTP 502 to the Ark controller — the Query phase will be overwritten by the controller's error handling
