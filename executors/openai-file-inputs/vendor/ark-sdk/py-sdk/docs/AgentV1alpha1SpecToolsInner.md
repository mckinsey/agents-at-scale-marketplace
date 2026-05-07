# AgentV1alpha1SpecToolsInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** | Description of the tool as exposed to the agent | [optional] 
**functions** | [**List[AgentV1alpha1SpecToolsInnerFunctionsInner]**](AgentV1alpha1SpecToolsInnerFunctionsInner.md) |  | [optional] 
**name** | **str** |  | [optional] 
**partial** | [**AgentV1alpha1SpecToolsInnerPartial**](AgentV1alpha1SpecToolsInnerPartial.md) |  | [optional] 
**type** | **str** |  | 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_tools_inner import AgentV1alpha1SpecToolsInner

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecToolsInner from a JSON string
agent_v1alpha1_spec_tools_inner_instance = AgentV1alpha1SpecToolsInner.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecToolsInner.to_json())

# convert the object into a dict
agent_v1alpha1_spec_tools_inner_dict = agent_v1alpha1_spec_tools_inner_instance.to_dict()
# create an instance of AgentV1alpha1SpecToolsInner from a dict
agent_v1alpha1_spec_tools_inner_from_dict = AgentV1alpha1SpecToolsInner.from_dict(agent_v1alpha1_spec_tools_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


