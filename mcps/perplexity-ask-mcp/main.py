#!/usr/bin/env python3
"""
Perplexity Ask MCP Server (LegacyX-compatible).
Exposes a single tool 'ask' so that when registered as MCPServer "perplexity",
ARK creates Tool "perplexity-ask". Matches LegacyX demo_notes and beneficial_owners_indirect_squad.
Ref: https://github.com/ppl-ai/modelcontextprotocol
"""
import os
import json
from typing import List, Dict, Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "PerplexityAsk",
    stateless_http=True,
    host="0.0.0.0",
)

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")
PERPLEXITY_BASE_URL = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")


def _call_perplexity(messages: List[Dict[str, str]]) -> str:
    """Call Perplexity API with messages. Raises if key missing or API error."""
    if not PERPLEXITY_API_KEY:
        raise ValueError("PERPLEXITY_API_KEY is not set")
    url = f"{PERPLEXITY_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": messages,
        "max_tokens": 2048,
    }
    with httpx.Client(timeout=90.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


@mcp.tool()
def ask(messages: List[Dict[str, Any]]) -> str:
    """
    Ask Perplexity (conversational AI with real-time web search).
    LegacyX-compatible: pass messages as [{"role": "user", "content": "<your prompt>"}].
    """
    if not messages:
        return "Error: messages list cannot be empty. Use [{\"role\": \"user\", \"content\": \"<prompt>\"}]"
    # Normalize to list of {role, content}
    normalized = []
    for m in messages:
        if isinstance(m, dict):
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, dict):
                content = json.dumps(content)
            normalized.append({"role": str(role), "content": str(content)})
        else:
            normalized.append({"role": "user", "content": str(m)})
    return _call_perplexity(normalized)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
