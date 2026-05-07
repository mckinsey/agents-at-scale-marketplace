# EvaluatorV1alpha1SpecSelectorNamespaceSelector

NamespaceSelector for more complex namespace selection

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**match_expressions** | [**List[AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner]**](AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.md) | matchExpressions is a list of label selector requirements. The requirements are ANDed. | [optional] 
**match_labels** | **object** | matchLabels is a map of {key,value} pairs. A single {key,value} in the matchLabels map is equivalent to an element of matchExpressions, whose key field is \&quot;key\&quot;, the operator is \&quot;In\&quot;, and the values array contains only \&quot;value\&quot;. The requirements are ANDed. | [optional] 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1_spec_selector_namespace_selector import EvaluatorV1alpha1SpecSelectorNamespaceSelector

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1SpecSelectorNamespaceSelector from a JSON string
evaluator_v1alpha1_spec_selector_namespace_selector_instance = EvaluatorV1alpha1SpecSelectorNamespaceSelector.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1SpecSelectorNamespaceSelector.to_json())

# convert the object into a dict
evaluator_v1alpha1_spec_selector_namespace_selector_dict = evaluator_v1alpha1_spec_selector_namespace_selector_instance.to_dict()
# create an instance of EvaluatorV1alpha1SpecSelectorNamespaceSelector from a dict
evaluator_v1alpha1_spec_selector_namespace_selector_from_dict = EvaluatorV1alpha1SpecSelectorNamespaceSelector.from_dict(evaluator_v1alpha1_spec_selector_namespace_selector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


