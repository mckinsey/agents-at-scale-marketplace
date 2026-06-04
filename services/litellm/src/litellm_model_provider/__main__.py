"""Entrypoint: load config, wire the LiteLLM backend, run the reconcile loop."""

from __future__ import annotations

import logging
import os

from kubernetes import config as kube_config

from .backend import LiteLLMBackend
from .config import Config
from .k8s import K8s
from .provider import Provider


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # httpx logs every request at INFO — too noisy for a 60s poll loop.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # In-cluster when running as a pod; falls back to local kubeconfig for dev.
    try:
        kube_config.load_incluster_config()
    except kube_config.ConfigException:
        kube_config.load_kube_config()

    cfg = Config.load()
    backend = LiteLLMBackend(cfg.litellm_base_url, cfg.master_key)
    Provider(cfg, backend, K8s()).run()


if __name__ == "__main__":
    main()
