# EvaluationV1alpha1SpecConfigTemplate

Template for dynamically creating evaluations from query selectors

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config** | **object** | Default configuration for template-generated evaluations | 
**evaluator** | [**EvaluationV1alpha1SpecConfigTemplateEvaluator**](EvaluationV1alpha1SpecConfigTemplateEvaluator.md) |  | 
**name_prefix** | **str** | Name prefix for generated child evaluations (defaults to parent name) | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) | Default parameters for template-generated evaluations | [optional] 
**type** | **str** |  | 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_template import EvaluationV1alpha1SpecConfigTemplate

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigTemplate from a JSON string
evaluation_v1alpha1_spec_config_template_instance = EvaluationV1alpha1SpecConfigTemplate.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigTemplate.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_template_dict = evaluation_v1alpha1_spec_config_template_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigTemplate from a dict
evaluation_v1alpha1_spec_config_template_from_dict = EvaluationV1alpha1SpecConfigTemplate.from_dict(evaluation_v1alpha1_spec_config_template_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


