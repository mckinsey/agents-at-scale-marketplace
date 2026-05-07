# ModelV1alpha1SpecConfigOpenai

OpenAIModelConfig contains OpenAI specific parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_key** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**base_url** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) |  | [optional] 
**properties** | **object** |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_openai import ModelV1alpha1SpecConfigOpenai

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigOpenai from a JSON string
model_v1alpha1_spec_config_openai_instance = ModelV1alpha1SpecConfigOpenai.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigOpenai.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_openai_dict = model_v1alpha1_spec_config_openai_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigOpenai from a dict
model_v1alpha1_spec_config_openai_from_dict = ModelV1alpha1SpecConfigOpenai.from_dict(model_v1alpha1_spec_config_openai_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


