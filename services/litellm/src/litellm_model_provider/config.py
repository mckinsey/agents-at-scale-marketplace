"""Provider configuration.

The sync target set lives in provider-level config (a mounted ConfigMap), not in
namespace labels — entitlement decisions stay in one place that the platform team
controls. The master key is injected from a Secret as an env var, never written
to the ConfigMap.
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CONFIG_PATH = "/etc/litellm-model-provider/config.yaml"
MANAGED_BY = "litellm-model-provider"


class Target(BaseModel):
    """A namespace to provision into, with an optional model allow-list."""

    namespace: str
    # Empty means "every model LiteLLM exposes".
    models: list[str] = Field(default_factory=list)


class _LiteLLMSection(BaseModel):
    base_url: str = Field(
        default="http://litellm.ark-system.svc.cluster.local:4000", alias="baseUrl"
    )


class _FileConfig(BaseModel):
    """Shape of the mounted config.yaml (camelCase keys from the ConfigMap)."""

    litellm: _LiteLLMSection = Field(default_factory=_LiteLLMSection)
    reconcile_interval_seconds: int = Field(default=60, alias="reconcileIntervalSeconds")
    targets: list[Target] = Field(default_factory=list)
    vkey_secret_name: str = Field(default="litellm-vkey", alias="vkeySecretName")
    model_icon: str = Field(default="", alias="modelIcon")


class _Env(BaseSettings):
    """Environment-sourced settings (secrets and runtime paths)."""

    model_config = SettingsConfigDict(extra="ignore")

    litellm_master_key: str = Field(alias="LITELLM_MASTER_KEY")
    config_path: str = Field(default=DEFAULT_CONFIG_PATH, alias="CONFIG_PATH")
    # Identity for the provenance annotation on generated Models.
    pod_namespace: str = Field(default="ark-system", alias="POD_NAMESPACE")
    provider_name: str = Field(default=MANAGED_BY, alias="PROVIDER_NAME")


class Config(BaseModel):
    litellm_base_url: str
    master_key: str
    reconcile_interval_seconds: int
    targets: list[Target]
    # Secret name created in each tenant namespace holding the virtual key.
    vkey_secret_name: str
    # Dashboard icon stamped on generated Model resources.
    model_icon: str
    # Provenance "<namespace>/<name>" stamped on generated Models.
    provider_ref: str

    @staticmethod
    def load(path: str | None = None) -> "Config":
        env = _Env()  # type: ignore[call-arg]  # values come from the environment
        with open(path or env.config_path) as f:
            file_cfg = _FileConfig.model_validate(yaml.safe_load(f) or {})

        return Config(
            litellm_base_url=file_cfg.litellm.base_url,
            master_key=env.litellm_master_key,
            reconcile_interval_seconds=file_cfg.reconcile_interval_seconds,
            targets=file_cfg.targets,
            vkey_secret_name=file_cfg.vkey_secret_name,
            model_icon=file_cfg.model_icon,
            provider_ref=f"{env.pod_namespace}/{env.provider_name}",
        )
