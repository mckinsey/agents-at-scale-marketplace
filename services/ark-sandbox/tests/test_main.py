"""Tests for main.py entrypoint."""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from main import create_health_app, main, run_controller, run_mcp_server


class TestCreateHealthApp:
    def test_routes_mounted(self):
        mcp_app = Mock()
        lifespan = Mock()
        app = create_health_app(mcp_app, lifespan)

        paths = [getattr(r, "path", None) for r in app.routes]
        assert "/health" in paths

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_status(self):
        mcp_app = Mock()
        app = create_health_app(mcp_app, None)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "ark-sandbox"}


class TestRunController:
    @pytest.mark.asyncio
    async def test_success(self):
        with patch("kopf.operator", AsyncMock()) as mock_operator:
            await run_controller(asyncio.Event())
        mock_operator.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancelled_error_is_swallowed(self):
        with patch("kopf.operator", AsyncMock(side_effect=asyncio.CancelledError())):
            await run_controller(asyncio.Event())

    @pytest.mark.asyncio
    async def test_generic_exception_reraised(self):
        with patch("kopf.operator", AsyncMock(side_effect=RuntimeError("boom"))):
            with pytest.raises(RuntimeError):
                await run_controller(asyncio.Event())


class TestRunMcpServer:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_mcp_app = Mock()
        mock_mcp_app.http_app.return_value = Mock(lifespan=Mock())
        mock_app = Mock()
        mock_app.http_app.return_value = mock_mcp_app.http_app.return_value

        mock_server = Mock()
        mock_server.serve = AsyncMock()

        with patch("sandbox_mcp.server.create_app", return_value=mock_app):
            with patch("uvicorn.Config", return_value=Mock()):
                with patch("uvicorn.Server", return_value=mock_server):
                    await run_mcp_server(asyncio.Event())

        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancelled_error_is_swallowed(self):
        mock_app = Mock()
        mock_app.http_app.return_value = Mock(lifespan=Mock())
        mock_server = Mock()
        mock_server.serve = AsyncMock(side_effect=asyncio.CancelledError())

        with patch("sandbox_mcp.server.create_app", return_value=mock_app):
            with patch("uvicorn.Config", return_value=Mock()):
                with patch("uvicorn.Server", return_value=mock_server):
                    await run_mcp_server(asyncio.Event())

    @pytest.mark.asyncio
    async def test_generic_exception_reraised(self):
        mock_app = Mock()
        mock_app.http_app.return_value = Mock(lifespan=Mock())
        mock_server = Mock()
        mock_server.serve = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("sandbox_mcp.server.create_app", return_value=mock_app):
            with patch("uvicorn.Config", return_value=Mock()):
                with patch("uvicorn.Server", return_value=mock_server):
                    with pytest.raises(RuntimeError):
                        await run_mcp_server(asyncio.Event())


class TestMain:
    @pytest.mark.asyncio
    async def test_runs_both_tasks_and_stops(self):
        with patch("main.run_controller", AsyncMock(return_value=None)) as mock_controller:
            with patch("main.run_mcp_server", AsyncMock(return_value=None)) as mock_mcp_server:
                await main()

        mock_controller.assert_called_once()
        mock_mcp_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_exception_is_logged(self, caplog):
        with patch("main.run_controller", AsyncMock(side_effect=RuntimeError("boom"))):
            with patch("main.run_mcp_server", AsyncMock(return_value=None)):
                with caplog.at_level(logging.ERROR, logger="main"):
                    await main()

        assert "Task failed: boom" in caplog.text
