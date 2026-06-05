"""File storage provider abstraction.

Each provider implements upload/list/get/delete against a specific backend
(OpenAI, Anthropic, etc.). The file API routes delegate to whichever
provider is configured.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Base URLs whose /files endpoint rejects cursor pagination (e.g. LLM gateways
# that proxy the OpenAI API but 500 on the `after` param). Remembered so we
# don't pay a retry cascade on every list call.
_pagination_unsupported: set[str] = set()


@dataclass
class FileObject:
    id: str
    filename: str
    bytes: int
    created_at: int
    purpose: str
    provider: str
    status: str = "processed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "bytes": self.bytes,
            "created_at": self.created_at,
            "purpose": self.purpose,
            "provider": self.provider,
            "status": self.status,
        }


@dataclass
class DeleteResult:
    id: str
    deleted: bool

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "deleted": self.deleted}


@dataclass
class FileListing:
    """A file listing plus whether it covers everything upstream.

    ``complete=False`` means pagination could not be followed (unsupported by
    the upstream gateway) — callers must not treat absence from ``files`` as
    proof a file no longer exists.
    """

    files: list[FileObject] = field(default_factory=list)
    complete: bool = True


class FileProvider(ABC):
    name: str

    @abstractmethod
    async def upload(self, filename: str, content: bytes, purpose: str) -> FileObject:
        pass

    @abstractmethod
    async def list_files(self, purpose: str | None = None) -> FileListing:
        pass

    @abstractmethod
    async def get(self, file_id: str) -> FileObject:
        pass

    @abstractmethod
    async def delete(self, file_id: str) -> DeleteResult:
        pass


class OpenAIFileProvider(FileProvider):
    name = "openai"

    def __init__(self, api_key: str, base_url: str | None = None):
        from openai import AsyncOpenAI
        kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._base_url = base_url or "https://api.openai.com/v1"
        self._client = AsyncOpenAI(**kwargs)

    async def upload(self, filename: str, content: bytes, purpose: str) -> FileObject:
        result = await self._client.files.create(file=(filename, content), purpose=purpose)
        return FileObject(
            id=result.id,
            filename=result.filename,
            bytes=result.bytes,
            created_at=result.created_at,
            purpose=result.purpose,
            provider=self.name,
            status=result.status or "processed",
        )

    def _to_file_object(self, f: Any) -> FileObject:
        return FileObject(
            id=f.id,
            filename=f.filename,
            bytes=f.bytes,
            created_at=f.created_at,
            purpose=f.purpose,
            provider=self.name,
            status=f.status or "processed",
        )

    async def list_files(self, purpose: str | None = None) -> FileListing:
        from openai import APIStatusError

        kwargs: dict[str, Any] = {}
        if purpose:
            kwargs["purpose"] = purpose
        # Follow the cursor so large orgs aren't under-reported: callers prune
        # the per-agent index against this listing, and a partial page would
        # delete valid entries. Some gateways 500 on the `after` cursor param,
        # so pagination failures degrade to an incomplete listing (prune is
        # skipped) rather than failing the whole request.
        page = await self._client.files.list(**kwargs)
        files = [self._to_file_object(f) for f in page.data]
        if self._base_url in _pagination_unsupported:
            return FileListing(files=files, complete=not page.has_next_page())
        while page.has_next_page():
            try:
                page = await page.get_next_page()
            except APIStatusError as e:
                logger.warning(
                    "file list pagination unsupported by %s (%s); "
                    "returning first %d files as an incomplete listing",
                    self._base_url, e.status_code, len(files),
                )
                _pagination_unsupported.add(self._base_url)
                return FileListing(files=files, complete=False)
            files.extend(self._to_file_object(f) for f in page.data)
        return FileListing(files=files, complete=True)

    async def get(self, file_id: str) -> FileObject:
        result = await self._client.files.retrieve(file_id)
        return FileObject(
            id=result.id,
            filename=result.filename,
            bytes=result.bytes,
            created_at=result.created_at,
            purpose=result.purpose,
            provider=self.name,
            status=result.status or "processed",
        )

    async def delete(self, file_id: str) -> DeleteResult:
        result = await self._client.files.delete(file_id)
        return DeleteResult(id=result.id, deleted=result.deleted)


def create_provider(provider: str, api_key: str, base_url: str | None = None) -> FileProvider:
    if provider == "openai":
        return OpenAIFileProvider(api_key=api_key, base_url=base_url)
    raise ValueError(f"Unknown file provider: {provider}. Supported: openai")
