"""Tests for Starlette app wiring and the direct /execute REST endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ark_sdk.executor import Message

from openai_responses_executor import app as app_module


def _fake_request(body: dict):
    request = MagicMock()
    request.json = AsyncMock(return_value=body)
    return request


class TestCreateApp:
    def test_registers_execute_file_and_chat_routes(self):
        app = app_module.create_app()

        by_path: dict[str, set[str]] = {}
        for route in app.routes:
            path = getattr(route, "path", None)
            if path is None:
                continue
            by_path.setdefault(path, set()).update(getattr(route, "methods", None) or set())

        assert "POST" in by_path.get("/execute", set())
        assert "GET" in by_path.get("/", set())
        assert {"POST"} <= by_path.get("/v1/files", set())
        assert {"GET"} <= by_path.get("/v1/files", set())
        assert {"GET", "DELETE"} <= by_path.get("/v1/files/{file_id}", set())
        assert "POST" in by_path.get("/chat", set())
        assert "POST" in by_path.get("/chat/reset", set())


class TestExecuteEndpoint:
    @pytest.mark.asyncio
    async def test_success_returns_messages_from_executor(self):
        body = {"agent": {"name": "a"}, "userInput": {"role": "user", "content": "hi"}}
        request = _fake_request(body)
        reply = [Message(role="assistant", content="hello", name="a")]

        with patch.object(app_module, "ExecutionEngineRequest", side_effect=lambda **kw: kw), \
             patch.object(app_module.executor, "execute_agent", AsyncMock(return_value=reply)) as mock_execute:
            response = await app_module._execute(request)

        mock_execute.assert_awaited_once_with(body)
        payload = json.loads(response.body)
        assert response.status_code == 200
        assert payload["messages"][0]["content"] == "hello"
        assert not payload["error"]

    @pytest.mark.asyncio
    async def test_executor_failure_returns_500_with_error_message(self):
        request = _fake_request({"agent": {"name": "a"}, "userInput": {"role": "user", "content": "hi"}})

        with patch.object(app_module, "ExecutionEngineRequest", side_effect=lambda **kw: kw), \
             patch.object(app_module.executor, "execute_agent", AsyncMock(side_effect=RuntimeError("boom"))):
            response = await app_module._execute(request)

        payload = json.loads(response.body)
        assert response.status_code == 500
        assert payload["messages"] == []
        assert "boom" in payload["error"]

