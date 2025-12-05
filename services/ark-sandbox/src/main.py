"""Main entrypoint - runs both the Kubernetes controller and MCP server."""

import logging
import asyncio
import signal
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def run_controller(stop_event: asyncio.Event) -> None:
    """Run the kopf-based Kubernetes controller."""
    import kopf

    # Import handlers to register them with kopf
    from controller import sandbox, pool  # noqa: F401

    logger.info("Starting ARK Sandbox controller")

    # Create a kopf operator settings
    settings = kopf.OperatorSettings()
    settings.persistence.finalizer = "ark.mckinsey.com/sandbox-finalizer"
    settings.posting.level = logging.WARNING

    # Run kopf in the background
    try:
        await kopf.operator(
            clusterwide=True,
            settings=settings,
            stop_flag=stop_event,
        )
    except asyncio.CancelledError:
        logger.info("Controller task cancelled")
    except Exception as e:
        logger.error(f"Controller error: {e}")
        raise


def create_health_app(mcp_app, lifespan):
    """Wrap MCP app with health endpoint."""
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse

    async def health(request):
        return JSONResponse({"status": "healthy", "service": "ark-sandbox"})

    # Create a Starlette app that handles /health and mounts MCP at root
    # Pass lifespan from FastMCP to ensure proper initialization
    routes = [
        Route("/health", health),
        Mount("/", app=mcp_app),
    ]

    return Starlette(routes=routes, lifespan=lifespan)


async def run_mcp_server(stop_event: asyncio.Event) -> None:
    """Run the FastMCP server as HTTP on port 2628."""
    import uvicorn
    from sandbox_mcp.server import create_app

    logger.info("Starting ARK Sandbox MCP server on port 2628")

    app = create_app()

    # Get the ASGI app for HTTP transport and wrap with health endpoint
    # Pass lifespan from FastMCP to ensure proper initialization
    mcp_asgi_app = app.http_app()
    asgi_app = create_health_app(mcp_asgi_app, mcp_asgi_app.lifespan)

    config = uvicorn.Config(
        asgi_app,
        host="0.0.0.0",
        port=2628,
        log_level="info",
    )
    server = uvicorn.Server(config)

    try:
        # Run uvicorn server
        await server.serve()
    except asyncio.CancelledError:
        logger.info("MCP server task cancelled")
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        raise


async def main() -> None:
    """Main entrypoint - runs controller and MCP server concurrently."""
    logger.info("Starting ARK Sandbox service")

    stop_event = asyncio.Event()

    # Handle shutdown signals
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Create tasks for both components
    controller_task = asyncio.create_task(run_controller(stop_event))
    mcp_task = asyncio.create_task(run_mcp_server(stop_event))

    try:
        # Wait for either task to complete (or error)
        done, pending = await asyncio.wait(
            [controller_task, mcp_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # If one task completed, signal the other to stop
        stop_event.set()

        # Check for errors in completed tasks
        for task in done:
            if task.exception():
                logger.error(f"Task failed: {task.exception()}")

        # Wait for pending tasks to finish
        if pending:
            await asyncio.wait(pending, timeout=10.0)

    except asyncio.CancelledError:
        logger.info("Main task cancelled")
        stop_event.set()

    finally:
        # Cancel any remaining tasks
        for task in [controller_task, mcp_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    logger.info("ARK Sandbox service stopped")


if __name__ == "__main__":
    asyncio.run(main())

