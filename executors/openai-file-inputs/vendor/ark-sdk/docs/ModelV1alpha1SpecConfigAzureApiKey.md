# ModelV1alpha1SpecConfigAzureApiKey

Deprecated: Use auth.apiKey instead

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | [optional] 
**value_from** | [**AgentV1alpha1SpecToolsInnerFunctionsInnerValueFrom**](AgentV1alpha1SpecToolsInnerFunctionsInnerValueFrom.md) |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_azure_api_key import ModelV1alpha1SpecConfigAzureApiKey

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigAzureApiKey from a JSON string
model_v1alpha1_spec_config_azure_api_key_instance = ModelV1alpha1SpecConfigAzureApiKey.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigAzureApiKey.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_azure_api_key_dict = model_v1alpha1_spec_config_azure_api_key_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigAzureApiKey from a dict
model_v1alpha1_spec_config_azure_api_key_from_dict = ModelV1alpha1SpecConfigAzureApiKey.from_dict(model_v1alpha1_spec_config_azure_api_key_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


