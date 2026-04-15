"""Tests for SchedulerConfig parsing and defaults."""

import pytest

from claude_agent_scheduler.config import SchedulerConfig


class TestSchedulerConfigDefaults:
    def test_defaults(self) -> None:
        config = SchedulerConfig()
        assert config.session_idle_ttl == 1800
        assert config.shutdown_policy == "Delete"
        assert config.sandbox_ready_timeout == 60
        assert config.sandbox_template == "claude-agent-sdk"
        assert config.namespace == "default"
        assert config.max_active_sandboxes == 0


class TestSchedulerConfigFromYaml:
    def test_full_config(self) -> None:
        yaml_str = """
sessionIdleTTL: 3600
shutdownPolicy: Retain
sandboxReadyTimeout: 120
sandboxTemplate: claude-agent-sdk-large
namespace: my-namespace
maxActiveSandboxes: 50
"""
        config = SchedulerConfig.from_yaml(yaml_str)
        assert config.session_idle_ttl == 3600
        assert config.shutdown_policy == "Retain"
        assert config.sandbox_ready_timeout == 120
        assert config.sandbox_template == "claude-agent-sdk-large"
        assert config.namespace == "my-namespace"
        assert config.max_active_sandboxes == 50

    def test_partial_config_uses_defaults(self) -> None:
        yaml_str = "sessionIdleTTL: 900\n"
        config = SchedulerConfig.from_yaml(yaml_str)
        assert config.session_idle_ttl == 900
        assert config.shutdown_policy == "Delete"
        assert config.sandbox_ready_timeout == 60

    def test_empty_yaml_uses_defaults(self) -> None:
        config = SchedulerConfig.from_yaml("")
        assert config.session_idle_ttl == 1800
        assert config.shutdown_policy == "Delete"

    def test_unknown_keys_ignored(self) -> None:
        yaml_str = "sessionIdleTTL: 600\nunknownKey: value\n"
        config = SchedulerConfig.from_yaml(yaml_str)
        assert config.session_idle_ttl == 600
