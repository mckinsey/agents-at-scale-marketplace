# EvaluationV1alpha1SpecConfigItemsInnerEvaluator

Evaluator reference for this evaluation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**namespace** | **str** |  | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_items_inner_evaluator import EvaluationV1alpha1SpecConfigItemsInnerEvaluator

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigItemsInnerEvaluator from a JSON string
evaluation_v1alpha1_spec_config_items_inner_evaluator_instance = EvaluationV1alpha1SpecConfigItemsInnerEvaluator.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigItemsInnerEvaluator.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_items_inner_evaluator_dict = evaluation_v1alpha1_spec_config_items_inner_evaluator_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigItemsInnerEvaluator from a dict
evaluation_v1alpha1_spec_config_items_inner_evaluator_from_dict = EvaluationV1alpha1SpecConfigItemsInnerEvaluator.from_dict(evaluation_v1alpha1_spec_config_items_inner_evaluator_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


