# EvaluatorV1alpha1Spec

EvaluatorSpec defines the configuration for an evaluator that can assess query performance. This allows query evaluations to be executed by different evaluation frameworks and systems, rather than the built-in evaluation engine. Evaluators work as services that process evaluation requests for queries and provide performance assessments and scoring.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**address** | [**EvaluatorV1alpha1SpecAddress**](EvaluatorV1alpha1SpecAddress.md) |  | 
**description** | **str** | Description provides human-readable information about this evaluator | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) | Parameters to pass to evaluation requests | [optional] 
**selector** | [**EvaluatorV1alpha1SpecSelector**](EvaluatorV1alpha1SpecSelector.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1_spec import EvaluatorV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1Spec from a JSON string
evaluator_v1alpha1_spec_instance = EvaluatorV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1Spec.to_json())

# convert the object into a dict
evaluator_v1alpha1_spec_dict = evaluator_v1alpha1_spec_instance.to_dict()
# create an instance of EvaluatorV1alpha1Spec from a dict
evaluator_v1alpha1_spec_from_dict = EvaluatorV1alpha1Spec.from_dict(evaluator_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


