# AgentV1alpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** |  | [optional] 
**execution_engine** | [**AgentV1alpha1SpecExecutionEngine**](AgentV1alpha1SpecExecutionEngine.md) |  | [optional] 
**model_ref** | [**AgentV1alpha1SpecModelRef**](AgentV1alpha1SpecModelRef.md) |  | [optional] 
**output_schema** | **object** | JSON schema for structured output format | [optional] 
**overrides** | [**List[AgentV1alpha1SpecOverridesInner]**](AgentV1alpha1SpecOverridesInner.md) |  | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) | Parameters for template processing in the prompt field | [optional] 
**prompt** | **str** |  | [optional] 
**tools** | [**List[AgentV1alpha1SpecToolsInner]**](AgentV1alpha1SpecToolsInner.md) |  | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec import AgentV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1Spec from a JSON string
agent_v1alpha1_spec_instance = AgentV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1Spec.to_json())

# convert the object into a dict
agent_v1alpha1_spec_dict = agent_v1alpha1_spec_instance.to_dict()
# create an instance of AgentV1alpha1Spec from a dict
agent_v1alpha1_spec_from_dict = AgentV1alpha1Spec.from_dict(agent_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


