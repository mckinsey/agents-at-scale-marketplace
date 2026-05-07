# EvaluationV1alpha1SpecConfigTemplateEvaluator

Default evaluator reference for template-generated evaluations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**namespace** | **str** |  | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_template_evaluator import EvaluationV1alpha1SpecConfigTemplateEvaluator

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigTemplateEvaluator from a JSON string
evaluation_v1alpha1_spec_config_template_evaluator_instance = EvaluationV1alpha1SpecConfigTemplateEvaluator.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigTemplateEvaluator.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_template_evaluator_dict = evaluation_v1alpha1_spec_config_template_evaluator_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigTemplateEvaluator from a dict
evaluation_v1alpha1_spec_config_template_evaluator_from_dict = EvaluationV1alpha1SpecConfigTemplateEvaluator.from_dict(evaluation_v1alpha1_spec_config_template_evaluator_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


