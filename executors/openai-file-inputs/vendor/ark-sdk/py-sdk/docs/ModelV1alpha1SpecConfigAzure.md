# ModelV1alpha1SpecConfigAzure

AzureModelConfig contains Azure OpenAI specific parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_key** | [**ModelV1alpha1SpecConfigAzureApiKey**](ModelV1alpha1SpecConfigAzureApiKey.md) |  | [optional] 
**api_version** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**auth** | [**ModelV1alpha1SpecConfigAzureAuth**](ModelV1alpha1SpecConfigAzureAuth.md) |  | [optional] 
**base_url** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) |  | [optional] 
**properties** | **object** |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_azure import ModelV1alpha1SpecConfigAzure

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigAzure from a JSON string
model_v1alpha1_spec_config_azure_instance = ModelV1alpha1SpecConfigAzure.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigAzure.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_azure_dict = model_v1alpha1_spec_config_azure_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigAzure from a dict
model_v1alpha1_spec_config_azure_from_dict = ModelV1alpha1SpecConfigAzure.from_dict(model_v1alpha1_spec_config_azure_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


