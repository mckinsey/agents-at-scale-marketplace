# ModelV1alpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config** | [**ModelV1alpha1SpecConfig**](ModelV1alpha1SpecConfig.md) |  | 
**model** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**poll_interval** | **str** |  | [optional] [default to '1m']
**provider** | **str** | Provider specifies the AI provider client to use (openai, azure, bedrock, anthropic). | 
**type** | **str** | Type specifies the API capability of the model (e.g., completions, embeddings). Deprecated: The values \&quot;openai\&quot;, \&quot;azure\&quot;, \&quot;bedrock\&quot; are accepted for backward compatibility but will be removed in release 1.0. Use spec.provider instead. | [optional] [default to 'completions']

## Example

```python
from ark_sdk.models.model_v1alpha1_spec import ModelV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1Spec from a JSON string
model_v1alpha1_spec_instance = ModelV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1Spec.to_json())

# convert the object into a dict
model_v1alpha1_spec_dict = model_v1alpha1_spec_instance.to_dict()
# create an instance of ModelV1alpha1Spec from a dict
model_v1alpha1_spec_from_dict = ModelV1alpha1Spec.from_dict(model_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


