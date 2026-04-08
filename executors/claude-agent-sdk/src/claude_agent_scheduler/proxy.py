"""A2A reverse proxy: extract context_id, route to sandbox, forward request."""

import json
import logging
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import StatusCode

from .sandbox_manager import SandboxManager

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("claude-agent-scheduler")

PROXY_TIMEOUT = 600.0  # 10 minutes — agent execution can be long-running


def extract_context_id(body: bytes) -> tuple[str, bytes]:
    """Extract contextId from A2A JSON-RPC body and return (id, possibly-patched body).

    A2A uses JSON-RPC 2.0 with camelCase fields.
    The contextId lives at params.message.contextId.
    If missing, we generate one and inject it so the downstream executor uses it.
    """
    try:
        data = json.loads(body)
        message = data.get("params", {}).get("message", {})
        context_id = message.get("contextId") or ""
        if isinstance(context_id, str) and context_id.strip():
            return context_id.strip(), body
        # contextId missing or empty — generate and inject
        generated = str(uuid.uuid4())
        if isinstance(data.get("params", {}).get("message"), dict):
            data["params"]["message"]["contextId"] = generated
        return generated, json.dumps(data).encode()
    except (json.JSONDecodeError, AttributeError, TypeError):
        return str(uuid.uuid4()), body


def extract_response_context_id(body: bytes) -> str:
    """Extract contextId from an A2A JSON-RPC response.

    The executor's response is a JSON-RPC result containing a Task object
    with a top-level contextId field.
    """
    try:
        data = json.loads(body)
        result = data.get("result", {})
        if isinstance(result, dict):
            ctx = result.get("contextId", "")
            if isinstance(ctx, str) and ctx.strip():
                return ctx.strip()
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    return ""


def create_proxy_app(
    sandbox_manager: SandboxManager,
    lifespan: Any = None,
) -> FastAPI:
    """Create the FastAPI application with A2A proxy and health endpoints."""
    app = FastAPI(title="Claude Agent SDK Scheduler", lifespan=lifespan)

    http_client = httpx.AsyncClient(timeout=httpx.Timeout(PROXY_TIMEOUT, connect=10.0))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/")
    @app.post("/{path:path}")
    async def proxy_a2a(request: Request, path: str = "") -> Response:
        raw_body = await request.body()
        conversation_id, body = extract_context_id(raw_body)

        # Extract incoming trace context
        ctx = extract(carrier=dict(request.headers))
        token = attach(ctx)

        try:
            with tracer.start_as_current_span(
                "scheduler.route",
                attributes={"sandbox.conversation_id": conversation_id},
            ) as route_span:
                # Ensure sandbox exists for this conversation
                try:
                    info, is_new = await sandbox_manager.ensure_sandbox(conversation_id)
                except Exception as e:
                    route_span.set_status(StatusCode.ERROR, str(e))
                    route_span.record_exception(e)
                    logger.error("Sandbox creation failed for conversation=%s: %s", conversation_id, e)
                    return Response(
                        content=json.dumps({"error": f"Sandbox creation failed: {e}"}),
                        status_code=502,
                        media_type="application/json",
                    )

                route_span.set_attribute("sandbox.name", info.sandbox_name)
                route_span.set_attribute("sandbox.is_new", is_new)

                # Update activity timestamp
                sandbox_manager.touch(conversation_id)

                # Forward request to sandbox
                target_url = f"http://{info.service_fqdn}:8000/{path}"
                try:
                    response = await _proxy_request(http_client, request, body, target_url)

                    # Register response contextId as alias so follow-up queries
                    # using the executor-chosen ID route to the same sandbox
                    resp_ctx = extract_response_context_id(response.body)
                    if resp_ctx and resp_ctx != conversation_id:
                        sandbox_manager.add_alias(resp_ctx, conversation_id)

                    return response
                except httpx.ConnectError as e:
                    # Sandbox unreachable — attempt recovery
                    logger.warning(
                        "Sandbox unreachable for conversation=%s, attempting recovery: %s",
                        conversation_id,
                        e,
                    )
                    try:
                        info, _ = await sandbox_manager.recover_sandbox(conversation_id)
                        target_url = f"http://{info.service_fqdn}:8000/{path}"
                        response = await _proxy_request(http_client, request, body, target_url)
                        return response
                    except Exception as recovery_err:
                        route_span.set_status(StatusCode.ERROR, str(recovery_err))
                        route_span.record_exception(recovery_err)
                        return Response(
                            content=json.dumps({"error": f"Sandbox recovery failed: {recovery_err}"}),
                            status_code=502,
                            media_type="application/json",
                        )
                except Exception as e:
                    route_span.set_status(StatusCode.ERROR, str(e))
                    route_span.record_exception(e)
                    return Response(
                        content=json.dumps({"error": f"Proxy error: {e}"}),
                        status_code=502,
                        media_type="application/json",
                    )
        finally:
            detach(token)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await http_client.aclose()

    return app


async def _proxy_request(
    http_client: httpx.AsyncClient,
    request: Request,
    body: bytes,
    target_url: str,
) -> Response:
    """Forward HTTP request to sandbox and relay response."""
    with tracer.start_as_current_span(
        "scheduler.proxy.forward",
        attributes={"http.url": target_url},
    ) as proxy_span:
        # Build forwarded headers — drop hop-by-hop and length headers
        # httpx recalculates Content-Length from the body we pass
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)
        headers.pop("transfer-encoding", None)

        # Inject OTEL trace context into outgoing headers
        inject(carrier=headers)

        upstream_response = await http_client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

        proxy_span.set_attribute("http.status_code", upstream_response.status_code)

        # Build response headers, excluding transfer-encoding (handled by ASGI)
        response_headers = dict(upstream_response.headers)
        response_headers.pop("transfer-encoding", None)
        response_headers.pop("content-length", None)

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )
