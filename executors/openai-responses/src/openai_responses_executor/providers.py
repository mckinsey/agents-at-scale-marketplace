"""File storage provider abstraction.

Each provider implements upload/list/get/delete against a specific backend
(OpenAI, Anthropic, etc.). The file API routes delegate to whichever
provider is configured.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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


class FileProvider(ABC):
    name: str

    @abstractmethod
    async def upload(self, filename: str, content: bytes, purpose: str) -> FileObject:
        pass

    @abstractmethod
    async def list_files(self, purpose: str | None = None) -> list[FileObject]:
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

    async def list_files(self, purpose: str | None = None) -> list[FileObject]:
        kwargs: dict[str, Any] = {}
        if purpose:
            kwargs["purpose"] = purpose
        result = await self._client.files.list(**kwargs)
        return [
            FileObject(
                id=f.id,
                filename=f.filename,
                bytes=f.bytes,
                created_at=f.created_at,
                purpose=f.purpose,
                provider=self.name,
                status=f.status or "processed",
            )
            for f in result.data
        ]

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
