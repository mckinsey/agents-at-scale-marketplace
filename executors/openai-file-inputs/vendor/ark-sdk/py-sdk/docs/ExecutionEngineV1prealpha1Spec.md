# ExecutionEngineV1prealpha1Spec

ExecutionEngineSpec defines the configuration for an execution engine that can run agent workloads. This allows agents to be executed by different frameworks such as LangChain, AutoGen, or other agent execution systems, rather than the built-in OpenAI-compatible engine. Execution engines communicate via the A2A (Agent-to-Agent) protocol.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**address** | [**ExecutionEngineV1prealpha1SpecAddress**](ExecutionEngineV1prealpha1SpecAddress.md) |  | 
**description** | **str** | Description provides human-readable information about this execution engine | [optional] 

## Example

```python
from ark_sdk.models.execution_engine_v1prealpha1_spec import ExecutionEngineV1prealpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of ExecutionEngineV1prealpha1Spec from a JSON string
execution_engine_v1prealpha1_spec_instance = ExecutionEngineV1prealpha1Spec.from_json(json)
# print the JSON string representation of the object
print(ExecutionEngineV1prealpha1Spec.to_json())

# convert the object into a dict
execution_engine_v1prealpha1_spec_dict = execution_engine_v1prealpha1_spec_instance.to_dict()
# create an instance of ExecutionEngineV1prealpha1Spec from a dict
execution_engine_v1prealpha1_spec_from_dict = ExecutionEngineV1prealpha1Spec.from_dict(execution_engine_v1prealpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


