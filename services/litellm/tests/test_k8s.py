"""Tests for Kubernetes helpers that don't need an API server."""

from litellm_model_provider.k8s import sanitize_name


def test_sanitize_plain_model_id():
    assert sanitize_name("gpt-4o") == "gpt-4o"


def test_sanitize_provider_prefixed_id():
    # bedrock/anthropic.claude-3 has '/' and '.' which are invalid in names.
    out = sanitize_name("bedrock/anthropic.claude-3")
    assert out == "bedrock-anthropic-claude-3"
    assert all(c.isalnum() or c == "-" for c in out)


def test_sanitize_lowercases_and_trims():
    assert sanitize_name("GPT-4O.") == "gpt-4o"


def test_sanitize_truncates_to_253():
    assert len(sanitize_name("a" * 300)) == 253
