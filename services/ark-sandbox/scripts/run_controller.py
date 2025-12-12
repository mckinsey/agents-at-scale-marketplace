#!/usr/bin/env python3
"""Run just the Kubernetes controller for testing."""

import logging
import asyncio
import signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Run the controller."""
    import kopf
    
    # Import handlers to register them with kopf
    from controller import sandbox, pool  # noqa: F401
    
    logger.info("Starting ARK Sandbox controller (standalone)")
    
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    settings = kopf.OperatorSettings()
    settings.persistence.finalizer = "ark.mckinsey.com/sandbox-finalizer"
    settings.posting.level = logging.WARNING
    
    try:
        await kopf.operator(
            clusterwide=True,
            settings=settings,
            stop_flag=stop_event,
        )
    except asyncio.CancelledError:
        logger.info("Controller stopped")


if __name__ == "__main__":
    asyncio.run(main())


