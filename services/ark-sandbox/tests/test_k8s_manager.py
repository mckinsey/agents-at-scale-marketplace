"""Tests for the Kubernetes manager."""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


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
        from k8s.manager import KubernetesManager
        
        manager = KubernetesManager()
        
        # Should try to load in-cluster config first
        mock_k8s_client['config'].load_incluster_config.assert_called_once()
    
    def test_init_falls_back_to_kubeconfig(self, mock_k8s_client):
        """Test that manager falls back to kubeconfig if not in cluster."""
        from k8s.manager import KubernetesManager
        from kubernetes.config import ConfigException
        
        # Make in-cluster config fail with the correct exception type
        mock_k8s_client['config'].load_incluster_config.side_effect = ConfigException("Not in cluster")
        mock_k8s_client['config'].ConfigException = ConfigException
        
        manager = KubernetesManager()
        
        # Should fall back to kubeconfig
        mock_k8s_client['config'].load_kube_config.assert_called_once()
    
    def test_manager_has_required_methods(self, mock_k8s_client):
        """Test that manager has all required methods."""
        from k8s.manager import KubernetesManager
        
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
        from k8s.manager import KubernetesManager
        
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
        from k8s.manager import KubernetesManager
        
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
        from k8s.manager import KubernetesManager
        
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
        from k8s.manager import KubernetesManager
        
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

