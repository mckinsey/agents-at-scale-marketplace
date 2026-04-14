# Perplexity Ask MCP Server (LegacyX-compatible)

MCP server that exposes a single tool **`perplexity-ask`** for conversational AI with real-time web search via the Perplexity API. Matches the LegacyX KYC demo setup (see [MCP Perplexity Ask](https://github.com/ppl-ai/modelcontextprotocol) and LegacyX `demos/kyc-onboarding/*/docs/demo_notes.md`).

## Tool

- **perplexity-ask** (Ark Tool name when MCPServer is registered as `perplexity`): accepts `messages` in the form `[{"role": "user", "content": "<prompt>"}]` and returns the Perplexity model response.

## Requirements

- **Secret**: `web-search-credentials` with key `perplexity-api-key` (Perplexity API key from [Perplexity](https://www.perplexity.ai/)).

## Build and deploy (from KYC bundle)

```bash
cd demos/kyc-onboarding-bundle
make build-perplexity-mcp
```

Or deploy all MCPs (including this one):

```bash
make build
```

## Local run

```bash
export PERPLEXITY_API_KEY=your_key
pip install -r requirements.txt
python main.py
```

Server listens on port 8000; MCP endpoint at `/mcp` (streamable HTTP).
