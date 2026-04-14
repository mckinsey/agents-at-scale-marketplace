#!/usr/bin/env python3
"""Main entry point for the OpenAI Responses API executor."""

import logging
import os

import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .app import create_app


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port, access_log=True, log_level="info")


if __name__ == "__main__":
    main()
