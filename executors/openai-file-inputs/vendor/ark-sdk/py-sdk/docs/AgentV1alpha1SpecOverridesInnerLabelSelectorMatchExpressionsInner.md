# AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner

A label selector requirement is a selector that contains values, a key, and an operator that relates the key and values.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key** | **str** | key is the label key that the selector applies to. | 
**operator** | **str** | operator represents a key&#39;s relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. | 
**values** | **List[str]** | values is an array of string values. If the operator is In or NotIn, the values array must be non-empty. If the operator is Exists or DoesNotExist, the values array must be empty. This array is replaced during a strategic merge patch. | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_overrides_inner_label_selector_match_expressions_inner import AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner from a JSON string
agent_v1alpha1_spec_overrides_inner_label_selector_match_expressions_inner_instance = AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.to_json())

# convert the object into a dict
agent_v1alpha1_spec_overrides_inner_label_selector_match_expressions_inner_dict = agent_v1alpha1_spec_overrides_inner_label_selector_match_expressions_inner_instance.to_dict()
# create an instance of AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner from a dict
agent_v1alpha1_spec_overrides_inner_label_selector_match_expressions_inner_from_dict = AgentV1alpha1SpecOverridesInnerLabelSelectorMatchExpressionsInner.from_dict(agent_v1alpha1_spec_overrides_inner_label_selector_match_expressions_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


