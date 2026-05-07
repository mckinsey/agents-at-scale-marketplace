# AgentV1alpha1SpecOverridesInnerLabelSelector

A label selector is a label query over a set of resources. The result of matchLabels and matchExpressions are ANDed. An empty label selector matches all objects. A null label selector matches no objects.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**match_expressions** | [**List[AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner]**](AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.md) | matchExpressions is a list of label selector requirements. The requirements are ANDed. | [optional] 
**match_labels** | **object** | matchLabels is a map of {key,value} pairs. A single {key,value} in the matchLabels map is equivalent to an element of matchExpressions, whose key field is \&quot;key\&quot;, the operator is \&quot;In\&quot;, and the values array contains only \&quot;value\&quot;. The requirements are ANDed. | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_overrides_inner_label_selector import AgentV1alpha1SpecOverridesInnerLabelSelector

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecOverridesInnerLabelSelector from a JSON string
agent_v1alpha1_spec_overrides_inner_label_selector_instance = AgentV1alpha1SpecOverridesInnerLabelSelector.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecOverridesInnerLabelSelector.to_json())

# convert the object into a dict
agent_v1alpha1_spec_overrides_inner_label_selector_dict = agent_v1alpha1_spec_overrides_inner_label_selector_instance.to_dict()
# create an instance of AgentV1alpha1SpecOverridesInnerLabelSelector from a dict
agent_v1alpha1_spec_overrides_inner_label_selector_from_dict = AgentV1alpha1SpecOverridesInnerLabelSelector.from_dict(agent_v1alpha1_spec_overrides_inner_label_selector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


