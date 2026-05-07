# EvaluatorV1alpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**last_resolved_address** | **str** | LastResolvedAddress contains the actual resolved address value | [optional] 
**message** | **str** |  | [optional] 
**phase** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1_status import EvaluatorV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1Status from a JSON string
evaluator_v1alpha1_status_instance = EvaluatorV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1Status.to_json())

# convert the object into a dict
evaluator_v1alpha1_status_dict = evaluator_v1alpha1_status_instance.to_dict()
# create an instance of EvaluatorV1alpha1Status from a dict
evaluator_v1alpha1_status_from_dict = EvaluatorV1alpha1Status.from_dict(evaluator_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


