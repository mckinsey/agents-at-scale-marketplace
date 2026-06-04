"""Reconcile-logic tests using fake backend + k8s (no cluster, no LiteLLM)."""

from litellm_model_provider.config import Config, Target
from litellm_model_provider.k8s import MODELS_ANNOTATION, sanitize_name
from litellm_model_provider.provider import Provider


class FakeBackend:
    def __init__(self):
        self.created = []
        self.updated = []

    def list_models(self):
        return ["gpt-4o", "claude-3-5-sonnet", "bedrock/anthropic.claude-3"]

    def create_key(self, alias, models):
        self.created.append((alias, tuple(models)))
        return "sk-vkey-" + alias

    def update_key(self, token, models):
        self.updated.append((token, tuple(models)))


class _Secret:
    def __init__(self, annotations, token):
        self.metadata = type("M", (), {"annotations": annotations})()
        self.string_data = {"api-key": token}
        self.data = None


class FakeK8s:
    def __init__(self):
        self.secrets = {}
        self.models = {}
        self.deleted = []

    def get_secret(self, ns, name):
        return self.secrets.get((ns, name))

    def upsert_vkey_secret(self, ns, name, token, models):
        self.secrets[(ns, name)] = _Secret(
            {MODELS_ANNOTATION: ",".join(sorted(models))}, token
        )

    def list_managed_models(self, ns):
        return list(self.models.get(ns, []))

    def upsert_model(self, ns, model_id, base_url, vkey_secret, icon, provider_ref=""):
        self.models.setdefault(ns, [])
        name = sanitize_name(model_id)
        if name not in self.models[ns]:
            self.models[ns].append(name)

    def delete_model(self, ns, name):
        self.deleted.append((ns, name))
        self.models[ns] = [m for m in self.models.get(ns, []) if m != name]


def _config(targets):
    return Config(
        litellm_base_url="http://litellm:4000",
        master_key="sk-master",
        reconcile_interval_seconds=60,
        targets=targets,
        vkey_secret_name="litellm-vkey",
        model_icon="icon.png",
        provider_ref="ark-system/litellm-model-provider",
    )


def test_cold_sync_all_models_uses_unrestricted_key():
    b, k = FakeBackend(), FakeK8s()
    Provider(_config([Target(namespace="tenant-a")]), b, k).reconcile_once()

    # Unrestricted key (empty scope) so models added later need no key change.
    assert b.created == [("ark-tenant-a", ())]
    assert sorted(k.models["tenant-a"]) == [
        "bedrock-anthropic-claude-3",
        "claude-3-5-sonnet",
        "gpt-4o",
    ]


def test_cold_sync_subset_scopes_key_and_models():
    b, k = FakeBackend(), FakeK8s()
    Provider(_config([Target(namespace="tenant-b", models=["gpt-4o"])]), b, k).reconcile_once()

    assert b.created == [("ark-tenant-b", ("gpt-4o",))]
    assert k.models["tenant-b"] == ["gpt-4o"]


def test_warm_sync_is_idempotent():
    b, k = FakeBackend(), FakeK8s()
    p = Provider(_config([Target(namespace="tenant-a")]), b, k)
    p.reconcile_once()
    b.created.clear()
    p.reconcile_once()

    assert b.created == []  # secret already exists, no re-mint


def test_scope_change_rescopes_key_and_prunes():
    b, k = FakeBackend(), FakeK8s()
    cfg = _config([Target(namespace="tenant-b", models=["gpt-4o"])])
    p = Provider(cfg, b, k)
    p.reconcile_once()

    cfg.targets[0] = Target(namespace="tenant-b", models=["claude-3-5-sonnet"])
    b.updated.clear()
    p.reconcile_once()

    assert b.updated == [("sk-vkey-ark-tenant-b", ("claude-3-5-sonnet",))]
    assert ("tenant-b", "gpt-4o") in k.deleted
    assert k.models["tenant-b"] == ["claude-3-5-sonnet"]
