"""Basic tests for ark-sandbox service."""

import main
from k8s.manager import DEFAULT_IMAGE, DEFAULT_NAMESPACE, DEFAULT_TTL_MINUTES, KubernetesManager
from sandbox_mcp.server import create_app
from sandbox_mcp.tools import register_tools
from controller import pool, sandbox


def test_main_import():
    """Test that main module can be imported."""
    assert hasattr(main, 'main')
    assert hasattr(main, 'run_controller')
    assert hasattr(main, 'run_mcp_server')


def test_k8s_manager_import():
    """Test that KubernetesManager can be imported."""
    assert KubernetesManager is not None


def test_k8s_manager_constants():
    """Test that k8s manager has expected constants."""
    assert DEFAULT_IMAGE == "python:3.12-slim"
    assert DEFAULT_TTL_MINUTES == 120
    assert DEFAULT_NAMESPACE == "default"


def test_mcp_tools_import():
    """Test that MCP tools module can be imported."""
    assert register_tools is not None
    assert callable(register_tools)


def test_mcp_server_import():
    """Test that MCP server can be imported."""
    assert create_app is not None
    assert callable(create_app)


def test_controller_sandbox_import():
    """Test that sandbox controller can be imported."""
    assert hasattr(sandbox, 'sandbox_created')
    assert hasattr(sandbox, 'sandbox_deleted')
    assert hasattr(sandbox, 'sandbox_timer')


def test_controller_pool_import():
    """Test that pool controller can be imported."""
    assert hasattr(pool, 'pool_created')
    assert hasattr(pool, 'pool_deleted')
    assert hasattr(pool, 'pool_timer')
