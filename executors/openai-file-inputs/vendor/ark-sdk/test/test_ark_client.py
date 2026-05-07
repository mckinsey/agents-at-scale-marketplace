#!/usr/bin/env python3
"""
Generated unittest tests for ARK Kubernetes Client Classes

Auto-generated from OpenAPI schema - do not edit manually.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any
from kubernetes.client.rest import ApiException
from ark_sdk.versions import ARKResourceClient, ARKClientV1alpha1, ARKClientV1prealpha1


class BaseTestCase(unittest.TestCase):
    """Base test case with common fixtures"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Kubernetes API client
        self.config_patcher = patch('kubernetes.config.load_kube_config')
        self.incluster_patcher = patch('kubernetes.config.load_incluster_config')
        self.api_client_patcher = patch('kubernetes.client.ApiClient')
        self.custom_api_patcher = patch('kubernetes.client.CustomObjectsApi')
        
        self.config_patcher.start()
        self.incluster_patcher.start()
        mock_client = self.api_client_patcher.start()
        mock_custom_api = self.custom_api_patcher.start()
        
        self.mock_client_instance = Mock()
        self.mock_api_client = Mock()
        mock_client.return_value = self.mock_client_instance
        mock_custom_api.return_value = self.mock_api_client
        
        # Sample resource data
        self.sample_resource_data = {
            'apiVersion': 'test.io/v1',
            'kind': 'TestResource',
            'metadata': {
                'name': 'test-resource',
                'namespace': 'default'
            },
            'spec': {
                'field1': 'value1',
                'field2': 'value2'
            }
        }
    
    def tearDown(self):
        """Clean up patches"""
        self.config_patcher.stop()
        self.incluster_patcher.stop()
        self.api_client_patcher.stop()
        self.custom_api_patcher.stop()


class MockModel:
    """Mock model class for testing"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def model_dump(self, by_alias=True, exclude_unset=True):
        result = {}
        for key, value in self.__dict__.items():
            if value is not None or not exclude_unset:
                result[key] = value
        return result
    
    def dict(self, by_alias=True, exclude_unset=True):
        return self.model_dump(by_alias=by_alias, exclude_unset=exclude_unset)
class TestARKResourceClient(BaseTestCase):
    """Test cases for ARKResourceClient"""
    
    def test_create_resource(self):
        """Test creating a resource"""
        
        # Setup
        self.mock_api_client.create_namespaced_custom_object.return_value = self.sample_resource_data
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Create resource
        resource = MockModel(**self.sample_resource_data)
        result = client.create(resource)
        
        # Verify
        self.mock_api_client.create_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources",
            body=self.sample_resource_data
        )
        self.assertTrue(hasattr(result, 'metadata'))
    
    def test_get_resource(self):
        """Test getting a resource"""
        
        # Setup
        self.mock_api_client.get_namespaced_custom_object.return_value = self.sample_resource_data
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Get resource
        result = client.get("test-resource")
        
        # Verify
        self.mock_api_client.get_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources",
            name="test-resource"
        )
        self.assertTrue(hasattr(result, 'metadata'))
    
    def test_get_resource_not_found(self):
        """Test getting a non-existent resource"""
        
        # Setup
        api_exception = ApiException()
        api_exception.status = 404
        self.mock_api_client.get_namespaced_custom_object.side_effect = api_exception
        
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Get resource should raise exception
        with self.assertRaises(Exception) as context:
            client.get("non-existent")
        
        self.assertIn("not found", str(context.exception))
    
    def test_list_resources(self):
        """Test listing resources"""
        
        # Setup
        self.mock_api_client.list_namespaced_custom_object.return_value = {
            'items': [self.sample_resource_data, self.sample_resource_data]
        }
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # List resources
        results = client.list()
        
        # Verify
        self.mock_api_client.list_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources"
        )
        self.assertEqual(len(results), 2)
    
    def test_list_resources_with_label_selector(self):
        """Test listing resources with label selector"""
        
        # Setup
        self.mock_api_client.list_namespaced_custom_object.return_value = {'items': []}
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # List resources with label selector
        client.list(label_selector="app=test")
        
        # Verify
        self.mock_api_client.list_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources",
            label_selector="app=test"
        )
    
    def test_update_resource(self):
        """Test updating a resource"""
        
        # Setup
        self.mock_api_client.replace_namespaced_custom_object.return_value = self.sample_resource_data
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Update resource
        resource = MockModel(**self.sample_resource_data)
        result = client.update(resource)
        
        # Verify
        self.mock_api_client.replace_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources",
            name="test-resource",
            body=self.sample_resource_data
        )
        self.assertTrue(hasattr(result, 'metadata'))
    
    def test_patch_resource(self):
        """Test patching a resource"""
        
        # Setup
        self.mock_api_client.patch_namespaced_custom_object.return_value = self.sample_resource_data
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Patch resource
        patch_data = {'spec': {'field1': 'new-value'}}
        result = client.patch("test-resource", patch_data)
        
        # Verify
        self.mock_api_client.patch_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources",
            name="test-resource",
            body=patch_data
        )
        self.assertTrue(hasattr(result, 'metadata'))
    
    def test_delete_resource(self):
        """Test deleting a resource"""
        
        # Setup
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Delete resource
        client.delete("test-resource")
        
        # Verify
        self.mock_api_client.delete_namespaced_custom_object.assert_called_once_with(
            group="test.io",
            version="v1",
            namespace="default",
            plural="testresources",
            name="test-resource"
        )
    
    def test_delete_resource_not_found(self):
        """Test deleting a non-existent resource"""
        
        # Setup
        api_exception = ApiException()
        api_exception.status = 404
        self.mock_api_client.delete_namespaced_custom_object.side_effect = api_exception
        
        client = ARKResourceClient(
            api_version="test.io/v1",
            kind="TestResource",
            plural="testresources",
            model_class=MockModel,
            namespace="default"
        )
        
        # Delete should raise exception
        with self.assertRaises(Exception) as context:
            client.delete("non-existent")
        
        self.assertIn("not found", str(context.exception))


class TestARKClientV1alpha1(BaseTestCase):
    """Test cases for ARKClientV1alpha1"""
    
    def test_a2atasks_client_initialization(self):
        """Test a2atasks client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has a2atasks attribute
        self.assertTrue(hasattr(client, 'a2atasks'))
        self.assertEqual(client.a2atasks.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.a2atasks.kind, "A2ATask")
        self.assertEqual(client.a2atasks.plural, "a2atasks")
        self.assertEqual(client.a2atasks.namespace, "test-namespace")
    def test_agents_client_initialization(self):
        """Test agents client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has agents attribute
        self.assertTrue(hasattr(client, 'agents'))
        self.assertEqual(client.agents.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.agents.kind, "Agent")
        self.assertEqual(client.agents.plural, "agents")
        self.assertEqual(client.agents.namespace, "test-namespace")
    def test_mcpservers_client_initialization(self):
        """Test mcpservers client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has mcpservers attribute
        self.assertTrue(hasattr(client, 'mcpservers'))
        self.assertEqual(client.mcpservers.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.mcpservers.kind, "MCPServer")
        self.assertEqual(client.mcpservers.plural, "mcpservers")
        self.assertEqual(client.mcpservers.namespace, "test-namespace")
    def test_memories_client_initialization(self):
        """Test memories client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has memories attribute
        self.assertTrue(hasattr(client, 'memories'))
        self.assertEqual(client.memories.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.memories.kind, "Memory")
        self.assertEqual(client.memories.plural, "memories")
        self.assertEqual(client.memories.namespace, "test-namespace")
    def test_models_client_initialization(self):
        """Test models client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has models attribute
        self.assertTrue(hasattr(client, 'models'))
        self.assertEqual(client.models.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.models.kind, "Model")
        self.assertEqual(client.models.plural, "models")
        self.assertEqual(client.models.namespace, "test-namespace")
    def test_queries_client_initialization(self):
        """Test queries client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has queries attribute
        self.assertTrue(hasattr(client, 'queries'))
        self.assertEqual(client.queries.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.queries.kind, "Query")
        self.assertEqual(client.queries.plural, "queries")
        self.assertEqual(client.queries.namespace, "test-namespace")
    def test_teams_client_initialization(self):
        """Test teams client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has teams attribute
        self.assertTrue(hasattr(client, 'teams'))
        self.assertEqual(client.teams.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.teams.kind, "Team")
        self.assertEqual(client.teams.plural, "teams")
        self.assertEqual(client.teams.namespace, "test-namespace")
    def test_tools_client_initialization(self):
        """Test tools client is properly initialized"""
        client = ARKClientV1alpha1(namespace="test-namespace")
        
        # Verify client has tools attribute
        self.assertTrue(hasattr(client, 'tools'))
        self.assertEqual(client.tools.api_version, "ark.mckinsey.com/v1alpha1")
        self.assertEqual(client.tools.kind, "Tool")
        self.assertEqual(client.tools.plural, "tools")
        self.assertEqual(client.tools.namespace, "test-namespace")
    
    def test_namespace_inheritance(self):
        """Test namespace is inherited by all resource clients"""
        client = ARKClientV1alpha1(namespace="custom-namespace")
        
        # Verify all resource clients have the same namespace
        self.assertEqual(client.a2atasks.namespace, "custom-namespace")
        self.assertEqual(client.agents.namespace, "custom-namespace")
        self.assertEqual(client.mcpservers.namespace, "custom-namespace")
        self.assertEqual(client.memories.namespace, "custom-namespace")
        self.assertEqual(client.models.namespace, "custom-namespace")
        self.assertEqual(client.queries.namespace, "custom-namespace")
        self.assertEqual(client.teams.namespace, "custom-namespace")
        self.assertEqual(client.tools.namespace, "custom-namespace")


class TestARKClientV1prealpha1(BaseTestCase):
    """Test cases for ARKClientV1prealpha1"""
    
    def test_a2aservers_client_initialization(self):
        """Test a2aservers client is properly initialized"""
        client = ARKClientV1prealpha1(namespace="test-namespace")
        
        # Verify client has a2aservers attribute
        self.assertTrue(hasattr(client, 'a2aservers'))
        self.assertEqual(client.a2aservers.api_version, "ark.mckinsey.com/v1prealpha1")
        self.assertEqual(client.a2aservers.kind, "A2AServer")
        self.assertEqual(client.a2aservers.plural, "a2aservers")
        self.assertEqual(client.a2aservers.namespace, "test-namespace")
    def test_executionengines_client_initialization(self):
        """Test executionengines client is properly initialized"""
        client = ARKClientV1prealpha1(namespace="test-namespace")
        
        # Verify client has executionengines attribute
        self.assertTrue(hasattr(client, 'executionengines'))
        self.assertEqual(client.executionengines.api_version, "ark.mckinsey.com/v1prealpha1")
        self.assertEqual(client.executionengines.kind, "ExecutionEngine")
        self.assertEqual(client.executionengines.plural, "executionengines")
        self.assertEqual(client.executionengines.namespace, "test-namespace")
    
    def test_namespace_inheritance(self):
        """Test namespace is inherited by all resource clients"""
        client = ARKClientV1prealpha1(namespace="custom-namespace")
        
        # Verify all resource clients have the same namespace
        self.assertEqual(client.a2aservers.namespace, "custom-namespace")
        self.assertEqual(client.executionengines.namespace, "custom-namespace")

if __name__ == '__main__':
    unittest.main()
