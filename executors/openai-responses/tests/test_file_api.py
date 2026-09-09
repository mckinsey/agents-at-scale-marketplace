"""Tests for the provider-agnostic Files API + executor UI endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, NotFoundError
from starlette.applications import Starlette
from starlette.testclient import TestClient

from openai_responses_executor import file_api
from openai_responses_executor.providers import DeleteResult, FileObject


def _app():
    return Starlette(routes=file_api.file_api_routes)


@pytest.fixture
def client():
    return TestClient(_app())


def _file(id="file-1", filename="a.txt", purpose="user_data"):
    return FileObject(id=id, filename=filename, bytes=10, created_at=100, purpose=purpose, provider="openai")


def _status_error(status_code: int, message="boom") -> APIStatusError:
    resp = httpx.Response(status_code=status_code, request=httpx.Request("GET", "http://x"))
    return APIStatusError(message, response=resp, body=None)


def _not_found_error(file_id: str) -> NotFoundError:
    resp = httpx.Response(status_code=404, request=httpx.Request("GET", "http://x"))
    return NotFoundError("not found", response=resp, body=None)


class TestExecutorUi:
    def test_serves_ui_html(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestUploadFile:
    def test_uploads_allowed_extension_and_indexes_it(self, client):
        provider = MagicMock()
        provider.upload = AsyncMock(return_value=_file())
        mock_index = MagicMock()

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)), \
             patch.object(file_api, "get_index", return_value=mock_index):
            response = client.post("/v1/files", files={"file": ("a.txt", b"hello world", "text/plain")})

        assert response.status_code == 201
        assert response.json()["id"] == "file-1"
        provider.upload.assert_awaited_once()
        args = provider.upload.await_args.args
        assert args[0] == "a.txt" and args[1] == b"hello world"
        mock_index.add.assert_called_once_with(file_api.ENV_INDEX_KEY, "file-1")

    def test_disallowed_extension_returns_400(self, client):
        # The allow-list is the only thing stopping arbitrary uploads to the
        # upstream file provider — this is a security boundary, not a UX nicety.
        response = client.post("/v1/files", files={"file": ("a.exe", b"hi", "application/octet-stream")})

        assert response.status_code == 400
        assert "not supported" in response.json()["error"]

    def test_body_over_limit_returns_413(self, client):
        with patch.object(file_api.config, "max_upload_bytes", 5):
            response = client.post("/v1/files", files={"file": ("a.txt", b"way too long", "text/plain")})

        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_content_length_header_over_limit_short_circuits_before_parsing_form(self):
        # Rejecting on the header (before reading the body) avoids buffering
        # an oversized upload into pod memory.
        request = MagicMock()
        request.headers = {"content-length": "1000"}
        request.form = AsyncMock()

        with patch.object(file_api.config, "max_upload_bytes", 5):
            response = await file_api.upload_file(request)

        assert response.status_code == 413
        request.form.assert_not_awaited()

    def test_provider_resolution_failure_returns_400(self, client):
        # No silent fallback to the wrong OpenAI project when ?agent= fails to resolve.
        with patch.object(file_api, "_get_provider_for_request", AsyncMock(side_effect=ValueError("agent has no model"))):
            response = client.post("/v1/files", files={"file": ("a.txt", b"hi", "text/plain")})

        assert response.status_code == 400
        assert "agent has no model" in response.json()["error"]

    def test_index_failure_does_not_fail_the_upload(self, client):
        # The upload already succeeded upstream; a broken side-index must not
        # turn that into a user-facing failure.
        provider = MagicMock()
        provider.upload = AsyncMock(return_value=_file())

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)), \
             patch.object(file_api, "get_index", side_effect=RuntimeError("disk error")):
            response = client.post("/v1/files", files={"file": ("a.txt", b"hi", "text/plain")})

        assert response.status_code == 201


class TestListFiles:
    def test_uploaded_files_only_lists_from_index(self, client):
        provider = MagicMock()
        provider.get = AsyncMock(side_effect=[_file("file-1"), _file("file-2")])
        mock_index = MagicMock()
        mock_index.list_for_agent.return_value = ["file-1", "file-2"]

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)), \
             patch.object(file_api, "get_index", return_value=mock_index), \
             patch.object(file_api.config, "uploaded_files_only", True):
            response = client.get("/v1/files")

        assert [f["id"] for f in response.json()["data"]] == ["file-1", "file-2"]

    def test_uploaded_files_only_prunes_index_on_not_found(self, client):
        # Self-healing: a file deleted upstream (outside this executor) must
        # not keep showing up in the listing forever.
        provider = MagicMock()
        provider.get = AsyncMock(side_effect=[_not_found_error("file-1"), _file("file-2")])
        mock_index = MagicMock()
        mock_index.list_for_agent.return_value = ["file-1", "file-2"]

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)), \
             patch.object(file_api, "get_index", return_value=mock_index), \
             patch.object(file_api.config, "uploaded_files_only", True):
            response = client.get("/v1/files")

        mock_index.remove.assert_called_once_with(file_api.ENV_INDEX_KEY, "file-1")
        assert [f["id"] for f in response.json()["data"]] == ["file-2"]

    def test_disabled_uploaded_files_only_lists_directly_from_provider(self, client):
        provider = MagicMock()
        provider.list_files = AsyncMock(return_value=MagicMock(files=[_file("file-9")]))

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)), \
             patch.object(file_api.config, "uploaded_files_only", False):
            response = client.get("/v1/files")

        provider.list_files.assert_awaited_once_with(purpose=None)
        assert [f["id"] for f in response.json()["data"]] == ["file-9"]


class TestDeleteFile:
    def test_deletes_and_removes_from_index(self, client):
        provider = MagicMock()
        provider.delete = AsyncMock(return_value=DeleteResult(id="file-42", deleted=True))
        mock_index = MagicMock()

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)), \
             patch.object(file_api, "get_index", return_value=mock_index):
            response = client.delete("/v1/files/file-42")

        provider.delete.assert_awaited_once_with("file-42")
        mock_index.remove.assert_called_once_with(file_api.ENV_INDEX_KEY, "file-42")
        assert response.json() == {"id": "file-42", "deleted": True}


class TestMapsProviderErrors:
    def test_upstream_4xx_passes_through_status(self, client):
        provider = MagicMock()
        provider.get = AsyncMock(side_effect=_status_error(404, "gone"))

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)):
            response = client.get("/v1/files/file-1")

        assert response.status_code == 404
        assert "gone" in response.json()["error"]

    def test_upstream_5xx_maps_to_502(self, client):
        provider = MagicMock()
        provider.get = AsyncMock(side_effect=_status_error(500, "server exploded"))

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)):
            response = client.get("/v1/files/file-1")

        assert response.status_code == 502

    def test_connection_error_maps_to_502(self, client):
        provider = MagicMock()
        provider.get = AsyncMock(side_effect=APIConnectionError(request=httpx.Request("GET", "http://x")))

        with patch.object(file_api, "_get_provider_for_request", AsyncMock(return_value=provider)):
            response = client.get("/v1/files/file-1")

        assert response.status_code == 502


class TestGetProviderForRequest:
    @pytest.mark.asyncio
    async def test_agent_param_resolves_credentials(self):
        request = MagicMock()
        request.query_params = {"agent": "team-a/my-agent"}
        with patch.object(file_api, "resolve_agent_openai_credentials",
                           AsyncMock(return_value=("sk-agent", "https://x"))) as mock_resolve:
            provider = await file_api._get_provider_for_request(request)

        mock_resolve.assert_awaited_once_with("my-agent", "team-a")
        assert provider._client.api_key == "sk-agent"

    @pytest.mark.asyncio
    async def test_agent_that_cannot_resolve_raises(self):
        request = MagicMock()
        request.query_params = {"agent": "team-a/my-agent"}
        with patch.object(file_api, "resolve_agent_openai_credentials", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="no OpenAI model configured"):
                await file_api._get_provider_for_request(request)
