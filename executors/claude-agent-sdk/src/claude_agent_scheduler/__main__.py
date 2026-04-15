#!/usr/bin/env python3
"""Main entry point for the Claude Agent SDK scheduler."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from .config import ConfigWatcher, SchedulerConfig
from .observability import setup_otel
from .proxy import PROXY_TIMEOUT, create_proxy_app
from .sandbox_manager import SandboxManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    """Initialize and run the scheduler."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    configmap_name = os.getenv("SCHEDULER_CONFIGMAP", "claude-agent-sdk-scheduler-config")
    namespace = os.getenv("SCHEDULER_NAMESPACE", "default")

    setup_otel()

    config = SchedulerConfig()
    config_watcher = ConfigWatcher(configmap_name=configmap_name, namespace=namespace, config=config)
    sandbox_manager = SandboxManager(config=config)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(PROXY_TIMEOUT, connect=3.0),
        limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        await config_watcher.start()
        await sandbox_manager.warm_cache()
        reaper_task = asyncio.create_task(sandbox_manager.run_reaper())
        yield
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass
        await http_client.aclose()
        await sandbox_manager.close()
        await config_watcher.stop()

    app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=http_client, lifespan=lifespan)

    server_config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(server_config)

    await server.serve()


def main() -> None:
    """Main entry point."""
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
