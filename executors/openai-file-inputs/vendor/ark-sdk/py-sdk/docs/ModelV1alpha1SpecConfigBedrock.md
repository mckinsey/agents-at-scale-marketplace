# ModelV1alpha1SpecConfigBedrock

BedrockModelConfig contains AWS Bedrock specific parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**access_key_id** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**base_url** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**max_tokens** | **int** |  | [optional] 
**model_arn** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**properties** | **object** |  | [optional] 
**region** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**secret_access_key** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**session_token** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | [optional] 
**temperature** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config_bedrock import ModelV1alpha1SpecConfigBedrock

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfigBedrock from a JSON string
model_v1alpha1_spec_config_bedrock_instance = ModelV1alpha1SpecConfigBedrock.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfigBedrock.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_bedrock_dict = model_v1alpha1_spec_config_bedrock_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfigBedrock from a dict
model_v1alpha1_spec_config_bedrock_from_dict = ModelV1alpha1SpecConfigBedrock.from_dict(model_v1alpha1_spec_config_bedrock_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


