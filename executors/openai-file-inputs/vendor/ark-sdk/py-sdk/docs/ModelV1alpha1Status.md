# ModelV1alpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of a model&#39;s state | [optional] 
**resolved_address** | **str** | ResolvedAddress contains the actual resolved base URL value | [optional] 

## Example

```python
from ark_sdk.models.model_v1alpha1_status import ModelV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of ModelV1alpha1Status from a JSON string
model_v1alpha1_status_instance = ModelV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(ModelV1alpha1Status.to_json())

# convert the object into a dict
model_v1alpha1_status_dict = model_v1alpha1_status_instance.to_dict()
# create an instance of ModelV1alpha1Status from a dict
model_v1alpha1_status_from_dict = ModelV1alpha1Status.from_dict(model_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


