#!/usr/bin/env python3
"""Main entry point for the Claude Agent SDK scheduler."""

import asyncio
import logging
import os
import signal
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from .config import ConfigWatcher, SchedulerConfig
from .observability import setup_otel
from .proxy import create_proxy_app
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

    shutdown_event = asyncio.Event()

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        await config_watcher.start()
        await sandbox_manager.rebuild_map()
        reaper_task = asyncio.create_task(sandbox_manager.run_reaper())
        yield
        shutdown_event.set()
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass
        await sandbox_manager.close()
        await config_watcher.stop()

    app = create_proxy_app(sandbox_manager=sandbox_manager, lifespan=lifespan)

    server_config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(server_config)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    await server.serve()


def main() -> None:
    """Main entry point."""
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
