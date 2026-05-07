# ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity

AzureWorkloadIdentity configures Azure Workload Identity authentication

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**client_id** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**tenant_id** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_azure_auth_workload_identity import ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity from a JSON string
model_v1alpha1_spec_config_azure_auth_workload_identity_instance = ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_azure_auth_workload_identity_dict = model_v1alpha1_spec_config_azure_auth_workload_identity_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity from a dict
model_v1alpha1_spec_config_azure_auth_workload_identity_from_dict = ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity.from_dict(model_v1alpha1_spec_config_azure_auth_workload_identity_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


