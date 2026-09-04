"""Tests for the Kubernetes manager."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from k8s.manager import KubernetesManager
from kubernetes.client.rest import ApiException
from kubernetes.config import ConfigException


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client."""
    with patch('k8s.manager.config') as mock_config, \
         patch('k8s.manager.client') as mock_client:
        
        # Mock the API clients
        mock_core_api = Mock()
        mock_custom_api = Mock()
        
        mock_client.CoreV1Api.return_value = mock_core_api
        mock_client.CustomObjectsApi.return_value = mock_custom_api
        
        yield {
            'config': mock_config,
            'client': mock_client,
            'core_api': mock_core_api,
            'custom_api': mock_custom_api,
        }


class TestKubernetesManager:
    """Tests for KubernetesManager class."""
    
    def test_init_loads_config(self, mock_k8s_client):
        """Test that manager loads kubernetes config on init."""
        manager = KubernetesManager()
        
        # Should try to load in-cluster config first
        mock_k8s_client['config'].load_incluster_config.assert_called_once()
    
    def test_init_falls_back_to_kubeconfig(self, mock_k8s_client):
        """Test that manager falls back to kubeconfig if not in cluster."""
        # Make in-cluster config fail with the correct exception type
        mock_k8s_client['config'].load_incluster_config.side_effect = ConfigException("Not in cluster")
        mock_k8s_client['config'].ConfigException = ConfigException
        
        manager = KubernetesManager()
        
        # Should fall back to kubeconfig
        mock_k8s_client['config'].load_kube_config.assert_called_once()
    
    def test_manager_has_required_methods(self, mock_k8s_client):
        """Test that manager has all required methods."""
        manager = KubernetesManager()
        
        # Check for required methods
        assert hasattr(manager, 'create_pod')
        assert hasattr(manager, 'delete_pod')
        assert hasattr(manager, 'get_pod_status')
        assert hasattr(manager, 'execute_command')
        assert hasattr(manager, 'upload_file')
        assert hasattr(manager, 'download_file')
        
        # CRD methods
        assert hasattr(manager, 'create_sandbox_cr')
        assert hasattr(manager, 'get_sandbox_cr')
        assert hasattr(manager, 'delete_sandbox_cr')
        assert hasattr(manager, 'list_sandbox_crs')
        assert hasattr(manager, 'wait_for_sandbox_ready')
        assert hasattr(manager, 'claim_from_pool')


class TestPodOperations:
    """Tests for pod-related operations."""
    
    @pytest.mark.asyncio
    async def test_create_pod_basic(self, mock_k8s_client):
        """Test basic pod creation."""
        manager = KubernetesManager()
        
        # Mock the create_namespaced_pod call
        mock_pod = Mock()
        mock_pod.metadata = Mock()
        mock_pod.metadata.name = "test-sandbox"
        mock_k8s_client['core_api'].create_namespaced_pod.return_value = mock_pod
        
        result = await manager.create_pod(
            name="test-sandbox",
            namespace="default",
            image="python:3.12-slim",
            ttl_minutes=60,
        )
        
        assert result.metadata.name == "test-sandbox"
        mock_k8s_client['core_api'].create_namespaced_pod.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_pod_with_pvc(self, mock_k8s_client):
        """Test pod creation with PVC mount."""
        manager = KubernetesManager()
        
        mock_pod = Mock()
        mock_pod.metadata = Mock()
        mock_pod.metadata.name = "test-sandbox"
        mock_k8s_client['core_api'].create_namespaced_pod.return_value = mock_pod
        
        result = await manager.create_pod(
            name="test-sandbox",
            namespace="default",
            image="python:3.12-slim",
            ttl_minutes=60,
            pvc_name="workflow-data",
        )
        
        # Verify the pod spec includes the PVC volume mount
        call_args = mock_k8s_client['core_api'].create_namespaced_pod.call_args
        pod_spec = call_args[1]['body'] if 'body' in call_args[1] else call_args[0][1]
        
        # Check that volume was added
        assert result.metadata.name == "test-sandbox"


class TestSandboxCROperations:
    """Tests for Sandbox CR operations."""
    
    @pytest.mark.asyncio
    async def test_create_sandbox_cr(self, mock_k8s_client):
        """Test creating a Sandbox CR."""
        manager = KubernetesManager()
        
        mock_sandbox = {
            'metadata': {'name': 'test-sandbox', 'namespace': 'default'},
            'spec': {'image': 'python:3.12-slim'},
        }
        mock_k8s_client['custom_api'].create_namespaced_custom_object.return_value = mock_sandbox
        
        result = await manager.create_sandbox_cr(
            image="python:3.12-slim",
            namespace="default",
        )
        
        assert result['name'] == 'test-sandbox'
        mock_k8s_client['custom_api'].create_namespaced_custom_object.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_sandbox_crs(self, mock_k8s_client):
        """Test listing Sandbox CRs."""
        manager = KubernetesManager()
        
        mock_sandboxes = {
            'items': [
                {
                    'metadata': {'name': 'sandbox-1', 'namespace': 'default'},
                    'spec': {'image': 'python:3.12-slim'},
                    'status': {'phase': 'Running'},
                },
                {
                    'metadata': {'name': 'sandbox-2', 'namespace': 'default'},
                    'spec': {'image': 'node:20-slim'},
                    'status': {'phase': 'Pending'},
                },
            ]
        }
        mock_k8s_client['custom_api'].list_namespaced_custom_object.return_value = mock_sandboxes
        
        result = await manager.list_sandbox_crs(namespace="default")
        
        assert len(result) == 2
        assert result[0]['name'] == 'sandbox-1'
        assert result[1]['name'] == 'sandbox-2'


class TestGetSandboxCR:
    """Tests for get_sandbox_cr."""

    @pytest.mark.asyncio
    async def test_get_sandbox_cr_success(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].get_namespaced_custom_object.return_value = {
            'metadata': {'name': 'test-sandbox', 'namespace': 'default'},
            'spec': {'image': 'python:3.12-slim', 'ttlMinutes': 120},
            'status': {'phase': 'Running', 'podName': 'pod-1', 'podIP': '10.0.0.1'},
        }

        result = await manager.get_sandbox_cr('test-sandbox')

        assert result['name'] == 'test-sandbox'
        assert result['phase'] == 'Running'
        assert result['podName'] == 'pod-1'

    @pytest.mark.asyncio
    async def test_get_sandbox_cr_not_found(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].get_namespaced_custom_object.side_effect = ApiException(status=404)

        with pytest.raises(Exception, match="not found"):
            await manager.get_sandbox_cr('missing-sandbox')

    @pytest.mark.asyncio
    async def test_get_sandbox_cr_other_error(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].get_namespaced_custom_object.side_effect = ApiException(status=500, reason="boom")

        with pytest.raises(Exception, match="Failed to get sandbox"):
            await manager.get_sandbox_cr('test-sandbox')


class TestDeleteSandboxCR:
    """Tests for delete_sandbox_cr."""

    @pytest.mark.asyncio
    async def test_delete_sandbox_cr_success(self, mock_k8s_client):
        manager = KubernetesManager()
        result = await manager.delete_sandbox_cr('test-sandbox', namespace='default')

        assert result == {'name': 'test-sandbox', 'namespace': 'default', 'deleted': True}

    @pytest.mark.asyncio
    async def test_delete_sandbox_cr_not_found(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].delete_namespaced_custom_object.side_effect = ApiException(status=404)

        with pytest.raises(Exception, match="not found"):
            await manager.delete_sandbox_cr('missing-sandbox')

    @pytest.mark.asyncio
    async def test_delete_sandbox_cr_other_error(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].delete_namespaced_custom_object.side_effect = ApiException(status=500, reason="boom")

        with pytest.raises(Exception, match="Failed to delete sandbox"):
            await manager.delete_sandbox_cr('test-sandbox')


class TestUpdateSandboxStatus:
    """Tests for update_sandbox_status."""

    @pytest.mark.asyncio
    async def test_update_sandbox_status_success(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].get_namespaced_custom_object.return_value = {
            'metadata': {'name': 'test-sandbox'}, 'status': {},
        }

        await manager.update_sandbox_status('test-sandbox', 'default', {'phase': 'Running'})

        mock_k8s_client['custom_api'].patch_namespaced_custom_object_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_sandbox_status_error_reraised(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['custom_api'].get_namespaced_custom_object.side_effect = ApiException(status=500)

        with pytest.raises(ApiException):
            await manager.update_sandbox_status('test-sandbox', 'default', {'phase': 'Running'})


class TestWaitForSandboxReady:
    """Tests for wait_for_sandbox_ready."""

    @pytest.mark.asyncio
    async def test_returns_when_running(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'name': 'test-sandbox', 'phase': 'Running'})

        result = await manager.wait_for_sandbox_ready('test-sandbox')

        assert result['phase'] == 'Running'

    @pytest.mark.asyncio
    async def test_raises_when_terminated(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'name': 'test-sandbox', 'phase': 'Terminated'})

        with pytest.raises(Exception, match="terminated unexpectedly"):
            await manager.wait_for_sandbox_ready('test-sandbox')

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'name': 'test-sandbox', 'phase': 'Pending'})

        times = iter([0, 0, 200])
        fake_loop = Mock()
        fake_loop.time.side_effect = lambda: next(times)

        with patch('k8s.manager.asyncio.get_event_loop', return_value=fake_loop), \
             patch('k8s.manager.asyncio.sleep', new=AsyncMock()):
            with pytest.raises(Exception, match="did not become ready"):
                await manager.wait_for_sandbox_ready('test-sandbox', timeout_seconds=60)


class TestClaimFromPool:
    """Tests for claim_from_pool."""

    @pytest.mark.asyncio
    async def test_no_available_sandbox(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.list_sandbox_crs = AsyncMock(return_value=[])

        with pytest.raises(Exception, match="No available sandbox"):
            await manager.claim_from_pool('python-pool')

    @pytest.mark.asyncio
    async def test_claim_success(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.list_sandbox_crs = AsyncMock(return_value=[
            {'name': 'pool-sbx-1', 'phase': 'Running'},
        ])
        manager.get_sandbox_cr = AsyncMock(return_value={'name': 'pool-sbx-1', 'phase': 'Running'})
        mock_k8s_client['custom_api'].get_namespaced_custom_object.return_value = {
            'metadata': {'name': 'pool-sbx-1', 'labels': {}},
            'spec': {},
        }

        result = await manager.claim_from_pool('python-pool', pvc_name='workflow-data')

        assert result['name'] == 'pool-sbx-1'
        mock_k8s_client['custom_api'].patch_namespaced_custom_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_claim_api_error(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.list_sandbox_crs = AsyncMock(return_value=[
            {'name': 'pool-sbx-1', 'phase': 'Running'},
        ])
        mock_k8s_client['custom_api'].get_namespaced_custom_object.side_effect = ApiException(status=500, reason="boom")

        with pytest.raises(Exception, match="Failed to claim sandbox"):
            await manager.claim_from_pool('python-pool')


class TestCreatePodSpec:
    """Tests for create_pod_spec."""

    def test_with_owner_reference_and_pvc(self, mock_k8s_client):
        manager = KubernetesManager()
        pod = manager.create_pod_spec(
            name='test-sandbox',
            image='python:3.12-slim',
            ttl_minutes=60,
            pvc_name='workflow-data',
            owner_reference={
                'apiVersion': 'ark.mckinsey.com/v1alpha1',
                'kind': 'Sandbox',
                'name': 'test-sandbox',
                'uid': 'abc-123',
            },
        )

        owner_ref_call = mock_k8s_client['client'].V1OwnerReference.call_args
        assert owner_ref_call.kwargs['name'] == 'test-sandbox'

        pod_spec_call = mock_k8s_client['client'].V1PodSpec.call_args
        assert len(pod_spec_call.kwargs['volumes']) == 2


class TestCreatePodError:
    """Tests for create_pod error handling."""

    @pytest.mark.asyncio
    async def test_create_pod_api_error_reraised(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['core_api'].create_namespaced_pod.side_effect = ApiException(status=500)

        with pytest.raises(ApiException):
            await manager.create_pod(
                name='test-sandbox', namespace='default', image='python:3.12-slim', ttl_minutes=60,
            )


class TestDeletePod:
    """Tests for delete_pod."""

    @pytest.mark.asyncio
    async def test_delete_pod_success(self, mock_k8s_client):
        manager = KubernetesManager()
        await manager.delete_pod('test-sandbox', 'default')

        mock_k8s_client['core_api'].delete_namespaced_pod.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pod_not_found_swallowed(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['core_api'].delete_namespaced_pod.side_effect = ApiException(status=404)

        await manager.delete_pod('test-sandbox', 'default')

    @pytest.mark.asyncio
    async def test_delete_pod_other_error_raised(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['core_api'].delete_namespaced_pod.side_effect = ApiException(status=500)

        with pytest.raises(ApiException):
            await manager.delete_pod('test-sandbox', 'default')


class TestGetPodStatusAndIp:
    """Tests for get_pod_status and get_pod_ip."""

    @pytest.mark.asyncio
    async def test_get_pod_status_success(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_pod = Mock()
        mock_pod.status.phase = 'Running'
        mock_k8s_client['core_api'].read_namespaced_pod.return_value = mock_pod

        result = await manager.get_pod_status('test-sandbox', 'default')

        assert result == 'Running'

    @pytest.mark.asyncio
    async def test_get_pod_status_not_found(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['core_api'].read_namespaced_pod.side_effect = ApiException(status=404)

        result = await manager.get_pod_status('test-sandbox', 'default')

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pod_status_other_error_raised(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['core_api'].read_namespaced_pod.side_effect = ApiException(status=500)

        with pytest.raises(ApiException):
            await manager.get_pod_status('test-sandbox', 'default')

    @pytest.mark.asyncio
    async def test_get_pod_ip_success(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_pod = Mock()
        mock_pod.status.pod_ip = '10.0.0.5'
        mock_k8s_client['core_api'].read_namespaced_pod.return_value = mock_pod

        result = await manager.get_pod_ip('test-sandbox', 'default')

        assert result == '10.0.0.5'

    @pytest.mark.asyncio
    async def test_get_pod_ip_not_found(self, mock_k8s_client):
        manager = KubernetesManager()
        mock_k8s_client['core_api'].read_namespaced_pod.side_effect = ApiException(status=404)

        result = await manager.get_pod_ip('test-sandbox', 'default')

        assert result is None


class TestExecuteCommand:
    """Tests for execute_command."""

    @pytest.mark.asyncio
    async def test_sandbox_not_running(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'phase': 'Pending'})

        with pytest.raises(Exception, match="is not running"):
            await manager.execute_command('test-sandbox', 'echo hi')

    @pytest.mark.asyncio
    async def test_sandbox_has_no_pod(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'phase': 'Running', 'podName': None})

        with pytest.raises(Exception, match="has no pod"):
            await manager.execute_command('test-sandbox', 'echo hi')

    @pytest.mark.asyncio
    async def test_execute_command_success(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'phase': 'Running', 'podName': 'pod-1'})

        fake_resp = Mock()
        fake_resp.is_open.side_effect = [True, False]
        fake_resp.peek_stdout.return_value = True
        fake_resp.read_stdout.return_value = 'hello'
        fake_resp.peek_stderr.return_value = False
        fake_resp.returncode = 0

        with patch('k8s.manager.stream', return_value=fake_resp):
            result = await manager.execute_command('test-sandbox', 'echo hello')

        assert result['stdout'] == 'hello'
        assert result['exit_code'] == 0
        assert result['command'] == 'echo hello'

    @pytest.mark.asyncio
    async def test_execute_command_stream_error(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'phase': 'Running', 'podName': 'pod-1'})

        with patch('k8s.manager.stream', side_effect=ApiException(status=500, reason="boom")):
            with pytest.raises(Exception, match="Failed to execute command"):
                await manager.execute_command('test-sandbox', 'echo hi')


class TestUploadDownloadFile:
    """Tests for upload_file and download_file."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.execute_command = AsyncMock(return_value={'exit_code': 0, 'stdout': '', 'stderr': ''})

        result = await manager.upload_file('test-sandbox', '/workspace/test.py', 'print(1)')

        assert result['success'] is True
        assert result['path'] == '/workspace/test.py'

    @pytest.mark.asyncio
    async def test_upload_file_failure(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.execute_command = AsyncMock(return_value={'exit_code': 1, 'stdout': '', 'stderr': 'denied'})

        with pytest.raises(Exception, match="Failed to upload file"):
            await manager.upload_file('test-sandbox', '/workspace/test.py', 'print(1)')

    @pytest.mark.asyncio
    async def test_download_file_success(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.execute_command = AsyncMock(return_value={'exit_code': 0, 'stdout': 'print(1)', 'stderr': ''})

        result = await manager.download_file('test-sandbox', '/workspace/test.py')

        assert result['content'] == 'print(1)'

    @pytest.mark.asyncio
    async def test_download_file_failure(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.execute_command = AsyncMock(return_value={'exit_code': 1, 'stdout': '', 'stderr': 'missing'})

        with pytest.raises(Exception, match="Failed to download file"):
            await manager.download_file('test-sandbox', '/workspace/missing.py')


class TestGetSandboxLogs:
    """Tests for get_sandbox_logs."""

    @pytest.mark.asyncio
    async def test_get_sandbox_logs_success(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'podName': 'pod-1'})
        mock_k8s_client['core_api'].read_namespaced_pod_log.return_value = 'log output'

        result = await manager.get_sandbox_logs('test-sandbox')

        assert result['logs'] == 'log output'

    @pytest.mark.asyncio
    async def test_get_sandbox_logs_no_pod(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'podName': None})

        with pytest.raises(Exception, match="has no pod"):
            await manager.get_sandbox_logs('test-sandbox')

    @pytest.mark.asyncio
    async def test_get_sandbox_logs_pod_not_found(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'podName': 'pod-1'})
        mock_k8s_client['core_api'].read_namespaced_pod_log.side_effect = ApiException(status=404)

        with pytest.raises(Exception, match="not found"):
            await manager.get_sandbox_logs('test-sandbox')

    @pytest.mark.asyncio
    async def test_get_sandbox_logs_other_error(self, mock_k8s_client):
        manager = KubernetesManager()
        manager.get_sandbox_cr = AsyncMock(return_value={'podName': 'pod-1'})
        mock_k8s_client['core_api'].read_namespaced_pod_log.side_effect = ApiException(status=500, reason="boom")

        with pytest.raises(Exception, match="Failed to get sandbox logs"):
            await manager.get_sandbox_logs('test-sandbox')

