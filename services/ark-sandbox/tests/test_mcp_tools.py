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


async def _tool_fn(mcp, name):
    """Return a registered tool's underlying function via FastMCP's public API.

    These tests used to walk mcp._tool_manager._tools, which FastMCP dropped;
    get_tool is the supported equivalent. FunctionTool.fn is public.
    """
    tool = await mcp.get_tool(name)
    return tool.fn


class TestMCPToolsRegistration:
    """Tests for MCP tool registration."""

    async def test_tools_are_registered(self, mcp_app):
        """Test that all expected tools are registered."""
        mcp, _ = mcp_app

        # Get registered tool names
        tool_names = [tool.name for tool in await mcp.list_tools()]

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
        create_sandbox = await _tool_fn(mcp, 'create_sandbox')

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
        
        create_sandbox = await _tool_fn(mcp, 'create_sandbox')

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
        
        execute_command = await _tool_fn(mcp, 'execute_command')

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
        
        claim_sandbox = await _tool_fn(mcp, 'claim_sandbox_from_pool')

        result = await claim_sandbox(pool_name="python-pool")
        
        assert result['sandbox_id'] == 'pool-sandbox-abc123'
        assert result['status'] == 'Running'
        mock_k8s_manager.claim_from_pool.assert_called_with(
            pool_name='python-pool',
            pvc_name=None,
            namespace=None,
        )


class TestGetSandboxInfoTool:
    @pytest.mark.asyncio
    async def test_get_sandbox_info(self, mcp_app):
        mcp, mock_k8s_manager = mcp_app
        tool_fn = await _tool_fn(mcp, 'get_sandbox_info')

        result = await tool_fn(sandbox_id="test-sandbox")

        assert result['sandbox_id'] == 'test-sandbox'
        assert result['pod_ip'] == '10.0.0.1'
        mock_k8s_manager.get_sandbox_cr.assert_called_with(name='test-sandbox', namespace=None)


class TestUploadFileTool:
    @pytest.mark.asyncio
    async def test_upload_file(self, mcp_app):
        mcp, mock_k8s_manager = mcp_app
        tool_fn = await _tool_fn(mcp, 'upload_file')

        result = await tool_fn(sandbox_id="test-sandbox", path="/workspace/test.py", content="print('hi')")

        assert result['path'] == '/workspace/test.py'
        assert result['success'] is True
        mock_k8s_manager.upload_file.assert_called_with(
            sandbox_name='test-sandbox', path='/workspace/test.py', content="print('hi')", namespace=None,
        )


class TestDownloadFileTool:
    @pytest.mark.asyncio
    async def test_download_file(self, mcp_app):
        mcp, mock_k8s_manager = mcp_app
        tool_fn = await _tool_fn(mcp, 'download_file')

        result = await tool_fn(sandbox_id="test-sandbox", path="/workspace/test.py")

        assert result['content'] == 'print("hello")'
        mock_k8s_manager.download_file.assert_called_with(
            sandbox_name='test-sandbox', path='/workspace/test.py', namespace=None,
        )


class TestListSandboxesTool:
    @pytest.mark.asyncio
    async def test_list_sandboxes(self, mcp_app):
        mcp, mock_k8s_manager = mcp_app
        tool_fn = await _tool_fn(mcp, 'list_sandboxes')

        result = await tool_fn()

        assert len(result) == 1
        assert result[0]['sandbox_id'] == 'sandbox-1'
        mock_k8s_manager.list_sandbox_crs.assert_called_with(namespace=None)


class TestDeleteSandboxTool:
    @pytest.mark.asyncio
    async def test_delete_sandbox(self, mcp_app):
        mcp, mock_k8s_manager = mcp_app
        tool_fn = await _tool_fn(mcp, 'delete_sandbox')

        result = await tool_fn(sandbox_id="test-sandbox")

        assert result['deleted'] is True
        mock_k8s_manager.delete_sandbox_cr.assert_called_with(name='test-sandbox', namespace=None)


class TestGetSandboxLogsTool:
    @pytest.mark.asyncio
    async def test_get_sandbox_logs(self, mcp_app):
        mcp, mock_k8s_manager = mcp_app
        tool_fn = await _tool_fn(mcp, 'get_sandbox_logs')

        result = await tool_fn(sandbox_id="test-sandbox")

        assert result['sandbox_id'] == 'test-sandbox'
        assert 'Container started' in result['logs']
        mock_k8s_manager.get_sandbox_logs.assert_called_with(
            sandbox_name='test-sandbox', namespace=None, tail_lines=None,
        )


class TestToolErrorPaths:
    """Every tool wraps its body in try/except and re-raises as ToolError."""

    @pytest.mark.asyncio
    async def test_create_sandbox_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.create_sandbox_cr.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'create_sandbox')

        with pytest.raises(ToolError, match="Failed to create sandbox"):
            await tool_fn()

    @pytest.mark.asyncio
    async def test_get_sandbox_info_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.get_sandbox_cr.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'get_sandbox_info')

        with pytest.raises(ToolError, match="Failed to get sandbox info"):
            await tool_fn(sandbox_id="test-sandbox")

    @pytest.mark.asyncio
    async def test_execute_command_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.execute_command.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'execute_command')

        with pytest.raises(ToolError, match="Failed to execute command"):
            await tool_fn(sandbox_id="test-sandbox", command="echo hi")

    @pytest.mark.asyncio
    async def test_upload_file_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.upload_file.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'upload_file')

        with pytest.raises(ToolError, match="Failed to upload file"):
            await tool_fn(sandbox_id="test-sandbox", path="/workspace/test.py", content="x")

    @pytest.mark.asyncio
    async def test_download_file_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.download_file.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'download_file')

        with pytest.raises(ToolError, match="Failed to download file"):
            await tool_fn(sandbox_id="test-sandbox", path="/workspace/test.py")

    @pytest.mark.asyncio
    async def test_list_sandboxes_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.list_sandbox_crs.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'list_sandboxes')

        with pytest.raises(ToolError, match="Failed to list sandboxes"):
            await tool_fn()

    @pytest.mark.asyncio
    async def test_delete_sandbox_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.delete_sandbox_cr.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'delete_sandbox')

        with pytest.raises(ToolError, match="Failed to delete sandbox"):
            await tool_fn(sandbox_id="test-sandbox")

    @pytest.mark.asyncio
    async def test_get_sandbox_logs_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.get_sandbox_logs.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'get_sandbox_logs')

        with pytest.raises(ToolError, match="Failed to get sandbox logs"):
            await tool_fn(sandbox_id="test-sandbox")

    @pytest.mark.asyncio
    async def test_claim_sandbox_from_pool_error(self, mcp_app):
        from fastmcp.exceptions import ToolError

        mcp, mock_k8s_manager = mcp_app
        mock_k8s_manager.claim_from_pool.side_effect = RuntimeError("boom")
        tool_fn = await _tool_fn(mcp, 'claim_sandbox_from_pool')

        with pytest.raises(ToolError, match="Failed to claim sandbox from pool"):
            await tool_fn(pool_name="python-pool")


