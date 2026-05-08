"""File storage provider abstraction.

Each provider implements upload/list/get/delete against a specific backend
(OpenAI, Anthropic, S3, etc.). The file API routes delegate to whichever
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


class S3FileProvider(FileProvider):
    """S3-compatible file provider that proxies to the file-gateway service."""
    name = "s3"

    def __init__(self, gateway_url: str):
        self._gateway_url = gateway_url.rstrip("/")

    async def upload(self, filename: str, content: bytes, purpose: str) -> FileObject:
        import httpx
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, content)}
            data = {"prefix": purpose + "/"}
            resp = await client.post(f"{self._gateway_url}/files", files=files, data=data)
            resp.raise_for_status()
            result = resp.json()
            return FileObject(
                id=result["key"],
                filename=filename,
                bytes=result.get("size", len(content)),
                created_at=int(_parse_iso_timestamp(result.get("last_modified", ""))),
                purpose=purpose,
                provider=self.name,
            )

    async def list_files(self, purpose: str | None = None) -> list[FileObject]:
        import httpx
        params: dict[str, str] = {}
        if purpose:
            params["prefix"] = purpose + "/"
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._gateway_url}/files", params=params)
            resp.raise_for_status()
            result = resp.json()
            return [
                FileObject(
                    id=f["key"],
                    filename=f["key"].rsplit("/", 1)[-1],
                    bytes=f.get("size", 0),
                    created_at=int(_parse_iso_timestamp(f.get("last_modified", ""))),
                    purpose=f["key"].split("/")[0] if "/" in f["key"] else "",
                    provider=self.name,
                )
                for f in result.get("files", [])
            ]

    async def get(self, file_id: str) -> FileObject:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._gateway_url}/files", params={"prefix": file_id})
            resp.raise_for_status()
            result = resp.json()
            files = result.get("files", [])
            if not files:
                raise ValueError(f"File not found: {file_id}")
            f = files[0]
            return FileObject(
                id=f["key"],
                filename=f["key"].rsplit("/", 1)[-1],
                bytes=f.get("size", 0),
                created_at=int(_parse_iso_timestamp(f.get("last_modified", ""))),
                purpose=f["key"].split("/")[0] if "/" in f["key"] else "",
                provider=self.name,
            )

    async def delete(self, file_id: str) -> DeleteResult:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{self._gateway_url}/files/{file_id}")
            resp.raise_for_status()
            return DeleteResult(id=file_id, deleted=True)


def _parse_iso_timestamp(ts: str) -> float:
    if not ts:
        return 0
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0


_providers: dict[str, FileProvider] = {}


def get_provider(name: str) -> FileProvider:
    if name not in _providers:
        raise ValueError(f"Provider '{name}' not registered. Available: {list(_providers.keys())}")
    return _providers[name]


def register_provider(provider: FileProvider) -> None:
    _providers[provider.name] = provider


def list_providers() -> list[str]:
    return list(_providers.keys())


def create_provider(provider: str, api_key: str = "", base_url: str | None = None, gateway_url: str = "") -> FileProvider:
    if provider == "openai":
        return OpenAIFileProvider(api_key=api_key, base_url=base_url)
    if provider == "s3":
        if not gateway_url:
            raise ValueError("S3 provider requires gateway_url")
        return S3FileProvider(gateway_url=gateway_url)
    raise ValueError(f"Unknown file provider: {provider}. Supported: openai, s3")
