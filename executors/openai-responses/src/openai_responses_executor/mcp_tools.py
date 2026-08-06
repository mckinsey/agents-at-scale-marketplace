"""MCP client support for the OpenAI Responses executor.

The Responses API can't call a self-hosted/remote MCP server on every Azure
apiVersion, so this executor runs the MCP client itself:

1. `discover_mcp_function_tools` connects to each `request.mcpServers` entry,
   lists its tools, and translates the allow-listed ones into OpenAI ``function``
   tool declarations the model can call.
2. `call_mcp_tool` dispatches the model's ``function_call`` (or a prefetch step)
   back to the MCP server via ``tools/call``.

It also provides the helpers used by the deterministic-prefetch chain
(`render_args`, `bindable_dict`) — see the executor's prefetch handling.

Sessions are opened per call (short-lived); MCP list/call round-trips are cheap
relative to the model turns.
"""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Separator between the MCP server name and tool name in the synthesized OpenAI
# function name. OpenAI requires function names to match ^[a-zA-Z0-9_-]+$.
_NAME_SEP = "__"


def _parse_timeout_seconds(value: Any, default: float = 30.0) -> float:
    """Parse a Go-duration string ('30s', '1m30s') or a number into seconds."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        from ark_sdk.extensions.query import _parse_go_duration_to_seconds  # type: ignore

        return float(_parse_go_duration_to_seconds(value))
    except Exception:
        pass
    s = str(value).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        pass
    total = 0.0
    matched = False
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([hms])", s):
        matched = True
        total += float(num) * {"h": 3600, "m": 60, "s": 1}[unit]
    return total if matched else default


def _sanitize_function_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return cleaned[:64] or "tool"


def _normalize(name: str) -> str:
    """Normalize a tool name for allow-list matching (hyphen/underscore-insensitive)."""
    return re.sub(r"[-_]", "_", str(name or "").strip().lower())


def function_name_for(server_name: str, tool_name: str) -> str:
    """Collision-free OpenAI function name for an (MCP server, tool) pair."""
    return _sanitize_function_name(f"{server_name}{_NAME_SEP}{tool_name}")


@asynccontextmanager
async def _mcp_session(server: Any):
    """Open a ready ``ClientSession`` to an MCP server over http or sse transport."""
    from mcp import ClientSession

    url = getattr(server, "url", None)
    if not url:
        raise ValueError("MCPServerConfig has no url")
    transport = (getattr(server, "transport", None) or "http").lower()
    headers = getattr(server, "headers", None) or {}
    timeout_s = _parse_timeout_seconds(getattr(server, "timeout", None))

    if transport == "sse":
        from mcp.client.sse import sse_client

        async with sse_client(url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(
            url, headers=headers, timeout=timedelta(seconds=timeout_s)
        ) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


def _tool_to_function(server_name: str, tool: Any) -> dict[str, Any]:
    params = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "name": function_name_for(server_name, getattr(tool, "name", "tool")),
        "description": getattr(tool, "description", "") or "",
        "parameters": params,
    }


async def discover_mcp_function_tools(
    mcp_servers: list[Any],
) -> tuple[list[dict[str, Any]], dict[str, tuple[Any, str]]]:
    """Discover MCP tools and translate them to OpenAI function tools.

    Returns ``(function_tool_dicts, registry)`` where ``registry`` maps the
    synthesized function name -> ``(server_config, mcp_tool_name)``. Only tools
    named in each server's declared allow-list (``server.tools``, populated by
    the ARK SDK from the Agent's ``type: mcp`` Tool CRDs) are exposed. Servers
    that fail to connect are logged and skipped.
    """
    function_tools: list[dict[str, Any]] = []
    registry: dict[str, tuple[Any, str]] = {}

    for server in mcp_servers or []:
        server_name = getattr(server, "name", "mcp")
        allow_raw = list(getattr(server, "tools", None) or [])
        if not allow_raw:
            logger.info("MCP server %s declares no tools; skipping", server_name)
            continue
        allow = {_normalize(n) for n in allow_raw}
        try:
            async with _mcp_session(server) as session:
                listed = await session.list_tools()
                available = getattr(listed, "tools", None) or []
                matched: list[str] = []
                for tool in available:
                    tname = getattr(tool, "name", None)
                    if _normalize(tname) not in allow:
                        continue
                    fdict = _tool_to_function(server_name, tool)
                    function_tools.append(fdict)
                    registry[fdict["name"]] = (server, tname)  # real name for tools/call
                    matched.append(tname)
            if matched:
                logger.info("MCP server %s: exposed tool(s) %s", server_name, matched)
            else:
                logger.warning(
                    "MCP server %s: none of the declared tools %s matched; available: %s",
                    server_name, allow_raw, [getattr(t, "name", None) for t in available],
                )
        except Exception as exc:
            logger.warning("Failed to discover tools from MCP server %s: %s", server_name, exc)

    return function_tools, registry


def _serialize_tool_result(result: Any) -> Any:
    """Reduce a ``CallToolResult`` to a JSON-serializable value.

    Prefers structured content (unwrapping a lone ``{"result": ...}`` that some
    servers emit); otherwise concatenates text blocks.
    """
    structured = getattr(result, "structuredContent", None)
    if structured:
        if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
            return structured["result"]
        return structured
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(f"[{getattr(block, 'type', 'content')}]")
    return {"content": "\n".join(parts)} if parts else {"content": ""}


async def call_mcp_tool(server: Any, mcp_tool_name: str, arguments: dict[str, Any]) -> Any:
    """Invoke ``tools/call`` on an MCP server; return a JSON-serializable result.

    Errors are returned as ``{"error": ...}`` rather than raised so the caller
    (tool loop or prefetch chain) can continue.
    """
    try:
        async with _mcp_session(server) as session:
            result = await session.call_tool(mcp_tool_name, arguments=arguments)
        if getattr(result, "isError", False):
            return {"error": _serialize_tool_result(result)}
        return _serialize_tool_result(result)
    except Exception as exc:
        logger.warning("MCP tool call '%s' failed: %s", mcp_tool_name, exc)
        return {"error": f"MCP tool '{mcp_tool_name}' call failed: {exc}"}


# ---------------------------------------------------------------------------
# Prefetch-chain helpers
# ---------------------------------------------------------------------------


def clean_input_text(raw: str) -> str:
    """Extract the user text from the agent's raw input, for the {input} var.

    Handles the chat messages-array shape (``[{"role":"user","content":"X"}]``
    -> ``X``, an ARK convention); otherwise returns the raw string. No
    domain/app-specific parsing — any such semantics belong in the agent config.
    """
    import json as _json

    try:
        v = _json.loads(raw)
        if isinstance(v, list) and v:
            last = v[-1]
            if isinstance(last, dict) and last.get("content"):
                return str(last["content"]).strip()
    except (ValueError, TypeError):
        pass
    return str(raw).strip()


def render_query_template(template: str, subs: dict[str, str]) -> str:
    """Substitute {key} / {bind.field} placeholders from ``subs``, then tidy.

    Unresolved placeholders are removed and whitespace collapsed, so an empty
    binding doesn't leave a literal ``{ch.locality}`` in the string.
    """
    out = template or ""
    for k, v in subs.items():
        out = out.replace("{" + k + "}", str(v or ""))
    out = re.sub(r"\{[a-z0-9_.]+\}", "", out)   # drop unresolved placeholders (incl. dotted)
    return re.sub(r"\s+", " ", out).strip()


def render_args(args: dict[str, Any], subs: dict[str, str]) -> dict[str, Any]:
    """Render {placeholder} substitutions in the string values of an args dict."""
    rendered: dict[str, Any] = {}
    for k, v in (args or {}).items():
        rendered[k] = render_query_template(v, subs) if isinstance(v, str) else v
    return rendered


def bindable_dict(result: Any) -> dict[str, Any]:
    """Best-effort flat dict from a call_mcp_tool result, for chain templating."""
    if isinstance(result, dict):
        if set(result.keys()) == {"result"} and isinstance(result["result"], dict):
            return result["result"]
        return result
    return {}
