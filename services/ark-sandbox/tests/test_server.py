"""Tests for the MCP server app factory."""

import logging
from unittest.mock import Mock, patch

import pytest

from sandbox_mcp.server import create_app, lifespan


class TestCreateApp:
    def test_registers_all_tools(self):
        with patch("sandbox_mcp.server.KubernetesManager", return_value=Mock()):
            mcp = create_app()

        assert mcp.name == "ARK Sandbox 🏖️"


class TestLifespan:
    @pytest.mark.asyncio
    async def test_logs_startup_and_shutdown(self, caplog):
        with caplog.at_level(logging.INFO, logger="sandbox_mcp.server"):
            async with lifespan(Mock()):
                assert "Starting ARK Sandbox MCP server" in caplog.text
                assert "Shutting down ARK Sandbox MCP server" not in caplog.text

        assert "Shutting down ARK Sandbox MCP server" in caplog.text
