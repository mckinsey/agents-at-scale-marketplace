# AgentV1alpha1SpecToolsInnerPartial

ToolPartial allows overriding the tool's name and preconfiguring or hiding tool parameters from the agent. Parameters defined here are injected at runtime and are not visible or editable by the agent itself.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name to override the tool&#39;s name as exposed to the agent (optional) | [optional] 
**parameters** | [**List[AgentV1alpha1SpecToolsInnerFunctionsInner]**](AgentV1alpha1SpecToolsInnerFunctionsInner.md) | Parameters to preconfigure and hide from the agent; injected at runtime and not visible/editable by the agent (optional) | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_tools_inner_partial import AgentV1alpha1SpecToolsInnerPartial

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecToolsInnerPartial from a JSON string
agent_v1alpha1_spec_tools_inner_partial_instance = AgentV1alpha1SpecToolsInnerPartial.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecToolsInnerPartial.to_json())

# convert the object into a dict
agent_v1alpha1_spec_tools_inner_partial_dict = agent_v1alpha1_spec_tools_inner_partial_instance.to_dict()
# create an instance of AgentV1alpha1SpecToolsInnerPartial from a dict
agent_v1alpha1_spec_tools_inner_partial_from_dict = AgentV1alpha1SpecToolsInnerPartial.from_dict(agent_v1alpha1_spec_tools_inner_partial_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


