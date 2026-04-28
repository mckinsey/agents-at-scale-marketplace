"""A2A reverse proxy: extract contextId, route to sandbox, forward request."""

import json
import logging
import uuid
from typing import Any, Optional

import httpx
from ark_sdk.extensions.query import QUERY_EXTENSION_METADATA_KEY, QueryRef
from ark_sdk.query_status_updater import QueryStatusUpdater
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import StatusCode

from .sandbox_manager import SandboxCapacityError, SandboxManager

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("claude-agent-scheduler")

PROXY_TIMEOUT = 600.0  # 10 minutes — agent execution can be long-running


def _is_valid_uuid4(value: str) -> bool:
    """Check if a string is a valid UUID4."""
    try:
        parsed = uuid.UUID(value, version=4)
        return str(parsed) == value.lower()
    except (ValueError, AttributeError):
        return False


def _extract_query_ref_from_body(body: bytes) -> Optional[QueryRef]:
    """Extract QueryRef from A2A JSON-RPC message metadata.

    Returns None if the body is unparseable or the query extension metadata is missing.
    """
    try:
        data = json.loads(body)
        metadata = data.get("params", {}).get("message", {}).get("metadata", {})
        ref_data = metadata.get(QUERY_EXTENSION_METADATA_KEY)
        if not ref_data or not isinstance(ref_data, dict):
            return None
        name = ref_data.get("name")
        namespace = ref_data.get("namespace")
        if not name or not namespace:
            return None
        return QueryRef(name=name, namespace=namespace)
    except Exception:
        return None


def _jsonrpc_error(request_id: Any, code: int, message: str) -> bytes:
    """Build a JSON-RPC 2.0 error response."""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }).encode()


def extract_context_id(body: bytes) -> tuple[str, bytes, bool]:
    """Extract and validate contextId from A2A JSON-RPC body.

    Returns (context_id, body, is_new) where:
    - is_new=True: contextId was missing/empty, a UUID4 was generated and injected
    - is_new=False: contextId was a valid UUID4, passed through unchanged

    Raises ValueError if contextId is present but not a valid UUID4.
    """
    try:
        data = json.loads(body)
        message = data.get("params", {}).get("message", {})
        context_id = message.get("contextId") or ""

        if isinstance(context_id, str):
            context_id = context_id.strip()

        if not context_id:
            # No contextId — generate UUID4 and inject
            generated = str(uuid.uuid4())
            if isinstance(data.get("params", {}).get("message"), dict):
                data["params"]["message"]["contextId"] = generated
            return generated, json.dumps(data).encode(), True

        # contextId present — must be a valid UUID4
        if not _is_valid_uuid4(context_id):
            raise ValueError(
                f"Invalid contextId '{context_id}': must be a valid UUID4 "
                "or omitted for auto-generation"
            )

        return context_id, body, False

    except (json.JSONDecodeError, AttributeError, TypeError):
        # Unparseable body — generate UUID4, don't modify body
        return str(uuid.uuid4()), body, True


def create_proxy_app(
    sandbox_manager: SandboxManager,
    http_client: httpx.AsyncClient,
    lifespan: Any = None,
) -> FastAPI:
    """Create the FastAPI application with A2A proxy and health endpoints."""
    app = FastAPI(title="Claude Agent SDK Scheduler", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/")
    @app.post("/{path:path}")
    async def proxy_a2a(request: Request, path: str = "") -> Response:
        raw_body = await request.body()

        # Extract and parse JSON-RPC id for error responses
        request_id = None
        try:
            request_id = json.loads(raw_body).get("id")
        except (json.JSONDecodeError, AttributeError):
            pass

        # Validate and extract contextId
        try:
            conversation_id, body, is_new = extract_context_id(raw_body)
        except ValueError as e:
            return Response(
                content=_jsonrpc_error(request_id, -32602, str(e)),
                status_code=400,
                media_type="application/json",
            )

        # Extract incoming trace context
        ctx = extract(carrier=dict(request.headers))
        token = attach(ctx)

        try:
            with tracer.start_as_current_span(
                "scheduler.route",
                attributes={"sandbox.conversation_id": conversation_id, "sandbox.is_new": is_new},
            ) as route_span:
                # Build status updater for new conversations
                status_updater: Optional[QueryStatusUpdater] = None
                if is_new:
                    query_ref = _extract_query_ref_from_body(raw_body)
                    if query_ref:
                        status_updater = QueryStatusUpdater(query_ref)

                # Route to sandbox based on session type
                try:
                    if is_new:
                        if status_updater:
                            try:
                                await status_updater.update_query_phase(
                                    "provisioning", "ExecutorProvisioning", "Provisioning sandbox",
                                )
                            except Exception:
                                logger.warning("Failed to set provisioning status for conversation=%s", conversation_id, exc_info=True)
                        info = await sandbox_manager.create_sandbox(conversation_id)
                        if status_updater:
                            try:
                                await status_updater.update_query_phase(
                                    "running", "QueryRunning", "Query is running",
                                )
                            except Exception:
                                logger.warning("Failed to set running status for conversation=%s", conversation_id, exc_info=True)
                    else:
                        info = await sandbox_manager.get_sandbox(conversation_id)
                        if info is None:
                            return Response(
                                content=_jsonrpc_error(request_id, -32001, "Session not found or expired"),
                                status_code=404,
                                media_type="application/json",
                            )
                except SandboxCapacityError as e:
                    route_span.set_status(StatusCode.ERROR, str(e))
                    return Response(
                        content=_jsonrpc_error(request_id, -32000, str(e)),
                        status_code=503,
                        media_type="application/json",
                        headers={"Retry-After": "30"},
                    )
                except Exception as e:
                    route_span.set_status(StatusCode.ERROR, str(e))
                    route_span.record_exception(e)
                    logger.error("Sandbox creation failed for conversation=%s: %s", conversation_id, e)
                    return Response(
                        content=_jsonrpc_error(request_id, -32603, f"Sandbox creation failed: {e}"),
                        status_code=502,
                        media_type="application/json",
                    )

                route_span.set_attribute("sandbox.name", info.sandbox_name)
                route_span.set_attribute("sandbox.is_new", is_new)

                # Forward request to sandbox
                target_url = f"http://{info.service_fqdn}:8000/{path}"
                try:
                    response = await _proxy_request(http_client, request, body, target_url)

                    # Update last-activity annotation
                    try:
                        await sandbox_manager.update_last_activity(conversation_id)
                    except Exception:
                        logger.warning("Failed to update last-activity for conversation=%s", conversation_id, exc_info=True)

                    return response
                except httpx.ConnectError as e:
                    # Sandbox unreachable — attempt recovery
                    logger.warning(
                        "Sandbox unreachable for conversation=%s, attempting recovery: %s",
                        conversation_id,
                        e,
                    )
                    try:
                        info = await sandbox_manager.recover_sandbox(conversation_id)
                        target_url = f"http://{info.service_fqdn}:8000/{path}"
                        response = await _proxy_request(http_client, request, body, target_url)
                        return response
                    except Exception as recovery_err:
                        route_span.set_status(StatusCode.ERROR, str(recovery_err))
                        route_span.record_exception(recovery_err)
                        return Response(
                            content=_jsonrpc_error(request_id, -32603, f"Sandbox recovery failed: {recovery_err}"),
                            status_code=502,
                            media_type="application/json",
                        )
                except Exception as e:
                    route_span.set_status(StatusCode.ERROR, str(e))
                    route_span.record_exception(e)
                    return Response(
                        content=_jsonrpc_error(request_id, -32603, f"Proxy error: {e}"),
                        status_code=502,
                        media_type="application/json",
                    )
        finally:
            detach(token)

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
