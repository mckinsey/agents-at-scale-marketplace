# ModelV1alpha1SpecConfig

ModelConfig holds type-specific configuration parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**anthropic** | [**ModelV1alpha1SpecConfigAnthropic**](ModelV1alpha1SpecConfigAnthropic.md) |  | [optional] 
**azure** | [**ModelV1alpha1SpecConfigAzure**](ModelV1alpha1SpecConfigAzure.md) |  | [optional] 
**bedrock** | [**ModelV1alpha1SpecConfigBedrock**](ModelV1alpha1SpecConfigBedrock.md) |  | [optional] 
**openai** | [**ModelV1alpha1SpecConfigOpenai**](ModelV1alpha1SpecConfigOpenai.md) |  | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_spec_config import ModelV1alpha1SpecConfig

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1SpecConfig from a JSON string
model_v1alpha1_spec_config_instance = ModelV1alpha1SpecConfig.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1SpecConfig.to_json())

# convert the object into a dict
model_v1alpha1_spec_config_dict = model_v1alpha1_spec_config_instance.to_dict()
# create an instance of ModelV1alpha1SpecConfig from a dict
model_v1alpha1_spec_config_from_dict = ModelV1alpha1SpecConfig.from_dict(model_v1alpha1_spec_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


