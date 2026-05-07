# EvaluationV1alpha1SpecConfigQuerySelector

Query selector for dynamic evaluation creation (requires template)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**match_expressions** | [**List[AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner]**](AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.md) | Field selector expressions | [optional] 
**match_labels** | **object** | Label selector | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_query_selector import EvaluationV1alpha1SpecConfigQuerySelector

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigQuerySelector from a JSON string
evaluation_v1alpha1_spec_config_query_selector_instance = EvaluationV1alpha1SpecConfigQuerySelector.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigQuerySelector.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_query_selector_dict = evaluation_v1alpha1_spec_config_query_selector_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigQuerySelector from a dict
evaluation_v1alpha1_spec_config_query_selector_from_dict = EvaluationV1alpha1SpecConfigQuerySelector.from_dict(evaluation_v1alpha1_spec_config_query_selector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


