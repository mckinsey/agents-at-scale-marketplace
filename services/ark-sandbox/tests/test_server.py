"""Tests for the MCP server app factory."""

import sys
import os
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestCreateApp:
    def test_registers_all_tools(self):
        from sandbox_mcp.server import create_app

        with patch("sandbox_mcp.server.KubernetesManager", return_value=Mock()):
            mcp = create_app()

        assert mcp.name == "ARK Sandbox 🏖️"


class TestLifespan:
    @pytest.mark.asyncio
    async def test_yields_once(self):
        from sandbox_mcp.server import lifespan

        async with lifespan(Mock()):
            pass
