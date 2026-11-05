"""Tests for the OpenAI Files API client wrapper and its connection cache."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import APIStatusError

from openai_responses_executor import providers
from openai_responses_executor.providers import OpenAIFileProvider, client_for


@pytest.fixture(autouse=True)
def _clear_module_state():
    providers._clients.clear()
    providers._pagination_unsupported.clear()
    yield
    providers._clients.clear()
    providers._pagination_unsupported.clear()


def _status_error(status_code: int) -> APIStatusError:
    resp = httpx.Response(status_code=status_code, request=httpx.Request("GET", "http://x"))
    return APIStatusError("boom", response=resp, body=None)


def _fake_file(id="file-1", filename="a.txt", bytes=10, created_at=100, purpose="user_data", status="processed"):
    f = MagicMock()
    f.id, f.filename, f.bytes, f.created_at, f.purpose, f.status = id, filename, bytes, created_at, purpose, status
    return f


class TestClientFor:
    def test_creates_client_with_given_credentials(self):
        with patch("openai.AsyncOpenAI") as mock_cls:
            client_for("sk-test", "https://proxy.example.com")

        mock_cls.assert_called_once_with(api_key="sk-test", base_url="https://proxy.example.com")

    def test_reuses_client_for_same_key(self):
        with patch("openai.AsyncOpenAI") as mock_cls:
            first = client_for("sk-test", "https://a.example.com")
            second = client_for("sk-test", "https://a.example.com")

        mock_cls.assert_called_once()
        assert first is second


class TestOpenAIFileProvider:
    def _provider(self, base_url=None):
        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            provider = OpenAIFileProvider(api_key="sk-test", base_url=base_url)
        return provider, mock_client

    @pytest.mark.asyncio
    async def test_upload_sends_filename_content_and_purpose(self):
        provider, mock_client = self._provider()
        mock_client.files.create = AsyncMock(return_value=_fake_file())

        result = await provider.upload("a.txt", b"hello", "user_data")

        mock_client.files.create.assert_awaited_once_with(file=("a.txt", b"hello"), purpose="user_data")
        assert result.id == "file-1" and result.filename == "a.txt"

    @pytest.mark.asyncio
    async def test_list_files_follows_pagination_cursor(self):
        provider, mock_client = self._provider()
        page1 = MagicMock()
        page1.data = [_fake_file("file-1")]
        page1.has_next_page.return_value = True
        page2 = MagicMock()
        page2.data = [_fake_file("file-2")]
        page2.has_next_page.return_value = False
        page1.get_next_page = AsyncMock(return_value=page2)
        mock_client.files.list = AsyncMock(return_value=page1)

        listing = await provider.list_files()

        page1.get_next_page.assert_awaited_once()
        assert [f.id for f in listing.files] == ["file-1", "file-2"]
        assert listing.complete is True

    @pytest.mark.asyncio
    async def test_list_files_pagination_unsupported_degrades_to_incomplete(self):
        provider, mock_client = self._provider(base_url="https://gateway.example.com")
        page = MagicMock()
        page.data = [_fake_file("file-1")]
        page.has_next_page.return_value = True
        page.get_next_page = AsyncMock(side_effect=_status_error(500))
        mock_client.files.list = AsyncMock(return_value=page)

        listing = await provider.list_files()

        assert listing.complete is False
        assert [f.id for f in listing.files] == ["file-1"]
        assert "https://gateway.example.com" in providers._pagination_unsupported

    @pytest.mark.asyncio
    async def test_get_retrieves_by_file_id(self):
        provider, mock_client = self._provider()
        mock_client.files.retrieve = AsyncMock(return_value=_fake_file("file-42"))

        result = await provider.get("file-42")

        mock_client.files.retrieve.assert_awaited_once_with("file-42")
        assert result.id == "file-42"

    @pytest.mark.asyncio
    async def test_delete_maps_provider_result(self):
        provider, mock_client = self._provider()
        deleted = MagicMock(id="file-42", deleted=True)
        mock_client.files.delete = AsyncMock(return_value=deleted)

        result = await provider.delete("file-42")

        mock_client.files.delete.assert_awaited_once_with("file-42")
        assert result.id == "file-42" and result.deleted is True
