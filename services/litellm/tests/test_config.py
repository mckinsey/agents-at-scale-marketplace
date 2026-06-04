"""Tests for config loading: camelCase ConfigMap keys, env-sourced master key."""

import pytest

from litellm_model_provider.config import Config


CONFIG_YAML = """
litellm:
  baseUrl: http://litellm.ark-system.svc.cluster.local:4000
reconcileIntervalSeconds: 30
vkeySecretName: my-vkey
modelIcon: icon.png
targets:
  - namespace: tenant-a
  - namespace: tenant-b
    models: [gpt-4o]
"""


def _write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return str(p)


def test_load_maps_camelcase_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    cfg = Config.load(_write(tmp_path, CONFIG_YAML))

    assert cfg.master_key == "sk-master"
    assert cfg.litellm_base_url.endswith(":4000")
    assert cfg.reconcile_interval_seconds == 30
    assert cfg.vkey_secret_name == "my-vkey"
    assert cfg.model_icon == "icon.png"
    assert [t.namespace for t in cfg.targets] == ["tenant-a", "tenant-b"]
    assert cfg.targets[0].models == []  # unrestricted
    assert cfg.targets[1].models == ["gpt-4o"]
    # Provenance ref derived from pod identity (defaults when env unset).
    assert cfg.provider_ref == "ark-system/litellm-model-provider"


def test_defaults_when_keys_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    cfg = Config.load(_write(tmp_path, "targets: []\n"))

    assert cfg.reconcile_interval_seconds == 60
    assert cfg.vkey_secret_name == "litellm-vkey"
    assert cfg.targets == []


def test_missing_master_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    with pytest.raises(Exception):
        Config.load(_write(tmp_path, "targets: []\n"))
