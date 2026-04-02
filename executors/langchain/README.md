# LangChain Executor

LangChain-based execution engine for Ark agents with RAG support.

## Features

- **LangChain Agent Execution** - Execute agents using LangChain with OpenAI and Azure OpenAI models
- **Conversation History** - Server-side conversation memory keyed by `conversationId`, using LangChain's `ChatMessageHistory`
- **RAG Support** - Retrieval Augmented Generation with FAISS vector search for code-aware responses
- **A2A Protocol** - Compliant with the Agent-to-Agent protocol for seamless integration
- **Health Checks** - Built-in health endpoint for Kubernetes liveness/readiness probes

## Quickstart

```bash
# Install with Ark CLI
ark marketplace install executor-langchain
```

## Development

```bash
# Local development with DevSpace
devspace dev
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

### Agent Labels

| Label | Value | Description |
|-------|-------|-------------|
| `langchain` | `rag` | Enables RAG functionality |
| `langchain-embeddings-model` | model name | Custom embeddings model |
