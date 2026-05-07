# EvaluatorV1alpha1SpecAddress

Address specifies how to reach the evaluator service

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | [optional] 
**value_from** | [**EvaluatorV1alpha1SpecAddressValueFrom**](EvaluatorV1alpha1SpecAddressValueFrom.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1_spec_address import EvaluatorV1alpha1SpecAddress

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1SpecAddress from a JSON string
evaluator_v1alpha1_spec_address_instance = EvaluatorV1alpha1SpecAddress.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1SpecAddress.to_json())

# convert the object into a dict
evaluator_v1alpha1_spec_address_dict = evaluator_v1alpha1_spec_address_instance.to_dict()
# create an instance of EvaluatorV1alpha1SpecAddress from a dict
evaluator_v1alpha1_spec_address_from_dict = EvaluatorV1alpha1SpecAddress.from_dict(evaluator_v1alpha1_spec_address_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


