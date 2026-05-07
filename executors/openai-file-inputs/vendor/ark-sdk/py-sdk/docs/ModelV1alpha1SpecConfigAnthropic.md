# ModelV1alpha1SpecConfigAnthropic

AnthropicModelConfig contains Anthropic API specific parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_key** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**base_url** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) |  | [optional] 
**properties** | **object** |  | [optional] 
**version** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_anthropic import ModelV1alpha1SpecConfigAnthropic

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigAnthropic from a JSON string
model_v1alpha1_spec_config_anthropic_instance = ModelV1alpha1SpecConfigAnthropic.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigAnthropic.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_anthropic_dict = model_v1alpha1_spec_config_anthropic_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigAnthropic from a dict
model_v1alpha1_spec_config_anthropic_from_dict = ModelV1alpha1SpecConfigAnthropic.from_dict(model_v1alpha1_spec_config_anthropic_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


