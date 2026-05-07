# EvaluationV1alpha1SpecEvaluator

EvaluationEvaluatorRef references an evaluator resource for evaluation with parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**namespace** | **str** |  | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_evaluator import EvaluationV1alpha1SpecEvaluator

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecEvaluator from a JSON string
evaluation_v1alpha1_spec_evaluator_instance = EvaluationV1alpha1SpecEvaluator.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecEvaluator.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_evaluator_dict = evaluation_v1alpha1_spec_evaluator_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecEvaluator from a dict
evaluation_v1alpha1_spec_evaluator_from_dict = EvaluationV1alpha1SpecEvaluator.from_dict(evaluation_v1alpha1_spec_evaluator_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


