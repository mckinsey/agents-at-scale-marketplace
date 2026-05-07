# AgentV1alpha1SpecOverridesInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) |  | 
**label_selector** | [**AgentV1alpha1SpecOverridesInnerLabelSelector**](AgentV1alpha1SpecOverridesInnerLabelSelector.md) |  | [optional] 
**resource_type** | **str** |  | 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_overrides_inner import AgentV1alpha1SpecOverridesInner

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecOverridesInner from a JSON string
agent_v1alpha1_spec_overrides_inner_instance = AgentV1alpha1SpecOverridesInner.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecOverridesInner.to_json())

# convert the object into a dict
agent_v1alpha1_spec_overrides_inner_dict = agent_v1alpha1_spec_overrides_inner_instance.to_dict()
# create an instance of AgentV1alpha1SpecOverridesInner from a dict
agent_v1alpha1_spec_overrides_inner_from_dict = AgentV1alpha1SpecOverridesInner.from_dict(agent_v1alpha1_spec_overrides_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


