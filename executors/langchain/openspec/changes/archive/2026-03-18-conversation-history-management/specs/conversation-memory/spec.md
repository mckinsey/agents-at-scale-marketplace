## ADDED Requirements

### Requirement: Conversation history lookup by conversationId
The executor SHALL maintain an in-memory store of conversation histories keyed by `conversationId`. When a request arrives, the executor SHALL retrieve the existing history for that `conversationId`, or create a new empty history if none exists.

#### Scenario: Existing conversation
- **WHEN** a request arrives with a `conversationId` that has prior history
- **THEN** the executor retrieves the existing `ChatMessageHistory` and uses its messages as context for the LLM invocation

#### Scenario: New conversation
- **WHEN** a request arrives with a `conversationId` that has no prior history
- **THEN** the executor creates a new `ChatMessageHistory` and prepends the agent's system prompt as a `SystemMessage`

### Requirement: User message appended to history before invocation
The executor SHALL append the current user message (including RAG context if applicable) to the conversation history before invoking the LLM.

#### Scenario: Standard message
- **WHEN** a request arrives without RAG enabled
- **THEN** the plain `userInput.content` is appended as a `HumanMessage` to the history

#### Scenario: RAG-augmented message
- **WHEN** a request arrives with RAG enabled and relevant code context found
- **THEN** the RAG-augmented content (context + user input) is appended as a `HumanMessage` to the history

### Requirement: Assistant response appended to history after invocation
The executor SHALL append the LLM response to the conversation history after a successful invocation.

#### Scenario: Successful response
- **WHEN** the LLM returns a response
- **THEN** the response content is appended as an `AIMessage` to the conversation history

### Requirement: History field no longer consumed
The executor SHALL NOT read or depend on a `history` field from the request. Conversation history is managed entirely server-side.

#### Scenario: Request without history field
- **WHEN** a request arrives with only `conversationId` (no `history` field)
- **THEN** the executor processes the request normally using its internal history store
