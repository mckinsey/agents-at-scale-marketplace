"""Scheduler configuration with ConfigMap watching and hot-reload."""

import asyncio
import logging
from typing import Any

import yaml
from kubernetes_asyncio import client, config, watch
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SchedulerConfig(BaseModel):
    """Scheduler configuration loaded from a ConfigMap."""

    session_idle_ttl: int = Field(default=1800, description="Idle session TTL in seconds (default 30m)")
    shutdown_policy: str = Field(default="Delete", description="Shutdown policy: Delete or Retain")
    sandbox_ready_timeout: int = Field(default=60, description="Sandbox readiness timeout in seconds")
    sandbox_template: str = Field(default="claude-agent-sdk", description="SandboxTemplate name")
    namespace: str = Field(default="default", description="Namespace for sandbox resources")

    @classmethod
    def from_yaml(cls, raw: str) -> "SchedulerConfig":
        """Parse config from a YAML string."""
        data = yaml.safe_load(raw) or {}
        return cls(**_normalize_keys(data))


def _normalize_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Convert camelCase keys to snake_case for pydantic."""
    mapping = {
        "sessionIdleTTL": "session_idle_ttl",
        "shutdownPolicy": "shutdown_policy",
        "sandboxReadyTimeout": "sandbox_ready_timeout",
        "sandboxTemplate": "sandbox_template",
        "namespace": "namespace",
    }
    return {mapping.get(k, k): v for k, v in data.items() if mapping.get(k, k) in SchedulerConfig.model_fields}


class ConfigWatcher:
    """Watches a ConfigMap and updates SchedulerConfig on changes."""

    def __init__(self, configmap_name: str, namespace: str, config: SchedulerConfig) -> None:
        self._configmap_name = configmap_name
        self._namespace = namespace
        self.config = config
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        """Load initial config and start background watch."""
        await self._load_initial()
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop the config watcher."""
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _load_initial(self) -> None:
        """Load config from ConfigMap on startup, fall back to defaults."""
        try:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                await config.load_kube_config()

            v1 = client.CoreV1Api()
            cm = await v1.read_namespaced_config_map(name=self._configmap_name, namespace=self._namespace)
            data = cm.data or {}
            if "config.yaml" in data:
                new_config = SchedulerConfig.from_yaml(data["config.yaml"])
                self._apply(new_config)
                logger.info("Loaded initial config from ConfigMap '%s'", self._configmap_name)
            else:
                logger.warning("ConfigMap '%s' has no 'config.yaml' key, using defaults", self._configmap_name)
        except Exception:
            logger.warning("ConfigMap '%s' not found or unreadable, using defaults", self._configmap_name)

    async def _watch_loop(self) -> None:
        """Watch ConfigMap for changes and apply updates."""
        while not self._stop.is_set():
            try:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    await config.load_kube_config()

                v1 = client.CoreV1Api()
                w = watch.Watch()
                try:
                    async for event in w.stream(
                        v1.list_namespaced_config_map,
                        namespace=self._namespace,
                        field_selector=f"metadata.name={self._configmap_name}",
                        timeout_seconds=300,
                    ):
                        if self._stop.is_set():
                            break
                        if event["type"] in ("ADDED", "MODIFIED"):
                            cm_data = event["object"].data or {}
                            if "config.yaml" in cm_data:
                                new_config = SchedulerConfig.from_yaml(cm_data["config.yaml"])
                                self._apply(new_config)
                                logger.info("Config updated from ConfigMap")
                finally:
                    await w.close()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("ConfigMap watch error, retrying in 5s")
                await asyncio.sleep(5)

    def _apply(self, new_config: SchedulerConfig) -> None:
        """Apply new config values to the shared config object."""
        for field_name in SchedulerConfig.model_fields:
            setattr(self.config, field_name, getattr(new_config, field_name))
