# EvaluationV1alpha1SpecConfigItemsInner

BatchEvaluationItem defines individual evaluation to create in batch mode

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config** | **object** | Configuration for this specific evaluation | 
**evaluator** | [**EvaluationV1alpha1SpecConfigItemsInnerEvaluator**](EvaluationV1alpha1SpecConfigItemsInnerEvaluator.md) |  | 
**name** | **str** | Name for the child evaluation (auto-generated if empty) | [optional] 
**timeout** | **str** | Timeout override for this evaluation | [optional] 
**ttl** | **str** | TTL override for this evaluation | [optional] 
**type** | **str** |  | 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_items_inner import EvaluationV1alpha1SpecConfigItemsInner

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigItemsInner from a JSON string
evaluation_v1alpha1_spec_config_items_inner_instance = EvaluationV1alpha1SpecConfigItemsInner.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigItemsInner.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_items_inner_dict = evaluation_v1alpha1_spec_config_items_inner_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigItemsInner from a dict
evaluation_v1alpha1_spec_config_items_inner_from_dict = EvaluationV1alpha1SpecConfigItemsInner.from_dict(evaluation_v1alpha1_spec_config_items_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


