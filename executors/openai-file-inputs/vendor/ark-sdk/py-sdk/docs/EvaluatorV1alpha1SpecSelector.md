# EvaluatorV1alpha1SpecSelector

Selector configuration for automatic query evaluation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_group** | **str** | APIGroup specifies the API group (e.g., \&quot;ark.mckinsey.com\&quot;) | [optional] [default to 'ark.mckinsey.com']
**match_expressions** | [**List[AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner]**](AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.md) | matchExpressions is a list of label selector requirements. The requirements are ANDed. | [optional] 
**match_labels** | **object** | matchLabels is a map of {key,value} pairs. A single {key,value} in the matchLabels map is equivalent to an element of matchExpressions, whose key field is \&quot;key\&quot;, the operator is \&quot;In\&quot;, and the values array contains only \&quot;value\&quot;. The requirements are ANDed. | [optional] 
**namespace_selector** | [**EvaluatorV1alpha1SpecSelectorNamespaceSelector**](EvaluatorV1alpha1SpecSelectorNamespaceSelector.md) |  | [optional] 
**namespaces** | **List[str]** | Namespaces to include (empty means all namespaces) | [optional] 
**resource_type** | **str** | ResourceType specifies the type of resource to select | 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1_spec_selector import EvaluatorV1alpha1SpecSelector

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1SpecSelector from a JSON string
evaluator_v1alpha1_spec_selector_instance = EvaluatorV1alpha1SpecSelector.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1SpecSelector.to_json())

# convert the object into a dict
evaluator_v1alpha1_spec_selector_dict = evaluator_v1alpha1_spec_selector_instance.to_dict()
# create an instance of EvaluatorV1alpha1SpecSelector from a dict
evaluator_v1alpha1_spec_selector_from_dict = EvaluatorV1alpha1SpecSelector.from_dict(evaluator_v1alpha1_spec_selector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


