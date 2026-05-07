# AgentV1alpha1SpecExecutionEngine

ExecutionEngine to use for running this agent. If not specified, uses the built-in OpenAI-compatible engine

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the ExecutionEngine resource to use for this agent | 
**namespace** | **str** | Namespace of the ExecutionEngine resource. Defaults to the agent&#39;s namespace if not specified | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_execution_engine import AgentV1alpha1SpecExecutionEngine

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecExecutionEngine from a JSON string
agent_v1alpha1_spec_execution_engine_instance = AgentV1alpha1SpecExecutionEngine.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecExecutionEngine.to_json())

# convert the object into a dict
agent_v1alpha1_spec_execution_engine_dict = agent_v1alpha1_spec_execution_engine_instance.to_dict()
# create an instance of AgentV1alpha1SpecExecutionEngine from a dict
agent_v1alpha1_spec_execution_engine_from_dict = AgentV1alpha1SpecExecutionEngine.from_dict(agent_v1alpha1_spec_execution_engine_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


