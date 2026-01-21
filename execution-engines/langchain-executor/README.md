# LangChain Executor

LangChain-based execution engine for Ark agents with optional RAG support.

## Quickstart

```bash
# Install with ARK CLI (recommended)
ark install marketplace/execution-engines/langchain-executor

# Or deploy with Helm
helm dependency update chart/
helm install langchain-executor ./chart --create-namespace

# Or deploy with DevSpace
devspace deploy
```

## Features

- LangChain framework integration
- Optional RAG (Retrieval-Augmented Generation) via agent labels
- Compatible with all Ark Model providers (Azure OpenAI, OpenAI, Ollama)
- Memory persistence for stateful conversations

## Usage

Reference the execution engine in your Agent:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: my-langchain-agent
spec:
  executionEngine:
    name: langchain-executor
  modelRef:
    name: default
  prompt: |
    You are a helpful assistant.
```

### Enable RAG

Add the `langchain: rag` label to enable retrieval-augmented generation:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: rag-agent
  labels:
    langchain: rag
spec:
  executionEngine:
    name: langchain-executor
  modelRef:
    name: default
  prompt: |
    You are a code expert. Use the provided context to answer questions.
```

### Custom Embeddings Model

Specify a custom embeddings model via label:

```yaml
metadata:
  labels:
    langchain: rag
    langchain-embeddings-model: text-embedding-3-small
```

## Development

```bash
make help     # Show available commands
make init     # Install dependencies
make dev      # Run in development mode
make test     # Run tests
```

## Configuration

See [chart/values.yaml](./chart/values.yaml) for all Helm configuration options.

Key settings:
- `replicaCount`: Number of replicas (default: 1)
- `resources`: CPU/memory limits
- `executionEngine.description`: Description shown in Ark
