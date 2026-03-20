#!/usr/bin/env python3
"""Main entry point for the Claude Agent SDK executor."""

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .app import app_instance


def main() -> None:
    """Main entry point."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    app_instance.run(host=host, port=port)


if __name__ == "__main__":
    main()
