"""Tests for MCP tools."""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_k8s_manager():
    """Create a mock KubernetesManager."""
    manager = Mock()
    
    # Mock async methods
    manager.create_sandbox_cr = AsyncMock(return_value={
        'name': 'test-sandbox',
        'namespace': 'default',
        'image': 'python:3.12-slim',
        'phase': 'Pending',
        'ttlMinutes': 120,
    })
    
    manager.wait_for_sandbox_ready = AsyncMock(return_value={
        'name': 'test-sandbox',
        'namespace': 'default',
        'image': 'python:3.12-slim',
        'phase': 'Running',
        'ttlMinutes': 120,
        'podName': 'test-sandbox-pod',
        'podIP': '10.0.0.1',
    })
    
    manager.get_sandbox_cr = AsyncMock(return_value={
        'name': 'test-sandbox',
        'namespace': 'default',
        'image': 'python:3.12-slim',
        'phase': 'Running',
        'ttlMinutes': 120,
        'podName': 'test-sandbox-pod',
        'podIP': '10.0.0.1',
        'startedAt': '2025-01-01T00:00:00Z',
        'expiresAt': '2025-01-01T02:00:00Z',
    })
    
    manager.execute_command = AsyncMock(return_value={
        'stdout': 'hello world',
        'stderr': '',
        'exit_code': 0,
        'command': 'echo hello world',
    })
    
    manager.upload_file = AsyncMock(return_value={
        'path': '/workspace/test.py',
        'size': 100,
        'success': True,
    })
    
    manager.download_file = AsyncMock(return_value={
        'path': '/workspace/test.py',
        'content': 'print("hello")',
    })
    
    manager.list_sandbox_crs = AsyncMock(return_value=[
        {
            'name': 'sandbox-1',
            'namespace': 'default',
            'image': 'python:3.12-slim',
            'phase': 'Running',
            'ttlMinutes': 120,
            'startedAt': '2025-01-01T00:00:00Z',
        },
    ])
    
    manager.delete_sandbox_cr = AsyncMock(return_value={
        'name': 'test-sandbox',
        'namespace': 'default',
        'deleted': True,
    })
    
    manager.get_sandbox_logs = AsyncMock(return_value={
        'logs': 'Container started\nReady to accept commands',
    })
    
    manager.claim_from_pool = AsyncMock(return_value={
        'name': 'pool-sandbox-abc123',
        'namespace': 'default',
        'image': 'python:3.12-slim',
        'phase': 'Running',
        'podName': 'pool-sandbox-abc123-pod',
        'podIP': '10.0.0.2',
    })
    
    return manager


@pytest.fixture
def mcp_app(mock_k8s_manager):
    """Create an MCP app with registered tools."""
    from fastmcp import FastMCP
    from sandbox_mcp.tools import register_tools
    
    mcp = FastMCP("Test Sandbox")
    register_tools(mcp, mock_k8s_manager)
    
    return mcp, mock_k8s_manager


class TestMCPToolsRegistration:
    """Tests for MCP tool registration."""
    
    def test_tools_are_registered(self, mcp_app):
        """Test that all expected tools are registered."""
        mcp, _ = mcp_app
        
        # Get registered tool names
        tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]
        
        expected_tools = [
            'create_sandbox',
            'get_sandbox_info',
            'execute_command',
            'upload_file',
            'download_file',
            'list_sandboxes',
            'delete_sandbox',
            'get_sandbox_logs',
            'claim_sandbox_from_pool',
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool {expected} not registered"


class TestCreateSandboxTool:
    """Tests for create_sandbox tool."""
    
    @pytest.mark.asyncio
    async def test_create_sandbox_basic(self, mock_k8s_manager):
        """Test basic sandbox creation."""
        from sandbox_mcp.tools import register_tools
        from fastmcp import FastMCP
        
        mcp = FastMCP("Test")
        register_tools(mcp, mock_k8s_manager)
        
        # Get the tool function
        create_sandbox = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == 'create_sandbox':
                create_sandbox = tool.fn
                break
        
        assert create_sandbox is not None
        
        result = await create_sandbox()
        
        assert result['sandbox_id'] == 'test-sandbox'
        assert result['status'] == 'Running'
        mock_k8s_manager.create_sandbox_cr.assert_called_once()
        mock_k8s_manager.wait_for_sandbox_ready.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_sandbox_with_pvc(self, mock_k8s_manager):
        """Test sandbox creation with PVC."""
        from sandbox_mcp.tools import register_tools
        from fastmcp import FastMCP
        
        mcp = FastMCP("Test")
        register_tools(mcp, mock_k8s_manager)
        
        create_sandbox = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == 'create_sandbox':
                create_sandbox = tool.fn
                break
        
        result = await create_sandbox(pvc_name="workflow-data")
        
        assert result['pvc_name'] == 'workflow-data'
        assert result['shared_path'] == '/shared'
        mock_k8s_manager.create_sandbox_cr.assert_called_with(
            image=None,
            namespace=None,
            ttl_minutes=None,
            pvc_name='workflow-data',
        )


class TestExecuteCommandTool:
    """Tests for execute_command tool."""
    
    @pytest.mark.asyncio
    async def test_execute_command(self, mock_k8s_manager):
        """Test command execution."""
        from sandbox_mcp.tools import register_tools
        from fastmcp import FastMCP
        
        mcp = FastMCP("Test")
        register_tools(mcp, mock_k8s_manager)
        
        execute_command = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == 'execute_command':
                execute_command = tool.fn
                break
        
        result = await execute_command(
            sandbox_id="test-sandbox",
            command="echo hello world",
        )
        
        assert result['stdout'] == 'hello world'
        assert result['exit_code'] == 0
        mock_k8s_manager.execute_command.assert_called_once()


class TestClaimFromPoolTool:
    """Tests for claim_sandbox_from_pool tool."""
    
    @pytest.mark.asyncio
    async def test_claim_from_pool(self, mock_k8s_manager):
        """Test claiming sandbox from pool."""
        from sandbox_mcp.tools import register_tools
        from fastmcp import FastMCP
        
        mcp = FastMCP("Test")
        register_tools(mcp, mock_k8s_manager)
        
        claim_sandbox = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == 'claim_sandbox_from_pool':
                claim_sandbox = tool.fn
                break
        
        result = await claim_sandbox(pool_name="python-pool")
        
        assert result['sandbox_id'] == 'pool-sandbox-abc123'
        assert result['status'] == 'Running'
        mock_k8s_manager.claim_from_pool.assert_called_with(
            pool_name='python-pool',
            pvc_name=None,
            namespace=None,
        )


