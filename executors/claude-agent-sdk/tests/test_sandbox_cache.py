"""Tests for SandboxCache TTL expiry, eviction, and warm loading (Task 1.2)."""

import time
from unittest.mock import patch

import pytest

from claude_agent_scheduler.sandbox_manager import SandboxCache, SandboxInfo


def _info(name: str = "sb-1") -> SandboxInfo:
    return SandboxInfo(claim_name=f"claim-{name}", sandbox_name=name, service_fqdn=f"{name}.ns.svc.cluster.local")


class TestSandboxCache:
    def test_put_and_get(self) -> None:
        cache = SandboxCache(ttl=10.0)
        info = _info()
        cache.put("conv-1", info)
        assert cache.get("conv-1") is info

    def test_miss_returns_none(self) -> None:
        cache = SandboxCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self) -> None:
        cache = SandboxCache(ttl=0.01)
        cache.put("conv-1", _info())
        time.sleep(0.02)
        assert cache.get("conv-1") is None

    def test_evict(self) -> None:
        cache = SandboxCache()
        cache.put("conv-1", _info())
        cache.evict("conv-1")
        assert cache.get("conv-1") is None

    def test_evict_nonexistent_is_noop(self) -> None:
        cache = SandboxCache()
        cache.evict("nonexistent")  # should not raise

    def test_warm(self) -> None:
        cache = SandboxCache()
        items = {"conv-1": _info("sb-1"), "conv-2": _info("sb-2")}
        cache.warm(items)
        assert cache.get("conv-1") is not None
        assert cache.get("conv-2") is not None
