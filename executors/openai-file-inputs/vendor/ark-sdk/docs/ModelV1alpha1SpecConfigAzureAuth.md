# ModelV1alpha1SpecConfigAzureAuth

AzureAuth represents authentication configuration for Azure OpenAI

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_key** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**managed_identity** | [**ModelV1alpha1SpecConfigAzureAuthManagedIdentity**](ModelV1alpha1SpecConfigAzureAuthManagedIdentity.md) |  | [optional] 
**workload_identity** | [**ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity**](ModelV1alpha1SpecConfigAzureAuthWorkloadIdentity.md) |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_azure_auth import ModelV1alpha1SpecConfigAzureAuth

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigAzureAuth from a JSON string
model_v1alpha1_spec_config_azure_auth_instance = ModelV1alpha1SpecConfigAzureAuth.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigAzureAuth.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_azure_auth_dict = model_v1alpha1_spec_config_azure_auth_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigAzureAuth from a dict
model_v1alpha1_spec_config_azure_auth_from_dict = ModelV1alpha1SpecConfigAzureAuth.from_dict(model_v1alpha1_spec_config_azure_auth_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


