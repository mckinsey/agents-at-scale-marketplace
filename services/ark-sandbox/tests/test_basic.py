"""Basic tests for ark-sandbox service."""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_main_import():
    """Test that main module can be imported."""
    import main
    assert hasattr(main, 'main')
    assert hasattr(main, 'run_controller')
    assert hasattr(main, 'run_mcp_server')


def test_k8s_manager_import():
    """Test that KubernetesManager can be imported."""
    from k8s.manager import KubernetesManager
    assert KubernetesManager is not None


def test_k8s_manager_constants():
    """Test that k8s manager has expected constants."""
    from k8s.manager import DEFAULT_IMAGE, DEFAULT_TTL_MINUTES, DEFAULT_NAMESPACE
    assert DEFAULT_IMAGE == "python:3.12-slim"
    assert DEFAULT_TTL_MINUTES == 120
    assert DEFAULT_NAMESPACE == "default"


def test_mcp_tools_import():
    """Test that MCP tools module can be imported."""
    from sandbox_mcp.tools import register_tools
    assert register_tools is not None
    assert callable(register_tools)


def test_mcp_server_import():
    """Test that MCP server can be imported."""
    from sandbox_mcp.server import create_app
    assert create_app is not None
    assert callable(create_app)


def test_controller_sandbox_import():
    """Test that sandbox controller can be imported."""
    from controller import sandbox
    assert hasattr(sandbox, 'sandbox_created')
    assert hasattr(sandbox, 'sandbox_deleted')
    assert hasattr(sandbox, 'sandbox_timer')


def test_controller_pool_import():
    """Test that pool controller can be imported."""
    from controller import pool
    assert hasattr(pool, 'pool_created')
    assert hasattr(pool, 'pool_deleted')
    assert hasattr(pool, 'pool_timer')


