"""ARK Sandbox MCP Server - Provides tools for managing sandbox containers."""

import logging
from contextlib import asynccontextmanager
from fastmcp import FastMCP

from k8s.manager import KubernetesManager
from sandbox_mcp.tools import register_tools

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Manage the MCP server lifecycle."""
    logger.info("Starting ARK Sandbox MCP server")
    yield
    logger.info("Shutting down ARK Sandbox MCP server")


def create_app():
    """Create the MCP server application."""
    mcp = FastMCP("ARK Sandbox 🏖️")
    k8s_manager = KubernetesManager()
    register_tools(mcp, k8s_manager)
    return mcp

