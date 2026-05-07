# ExecutionEngineV1prealpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**last_resolved_address** | **str** | LastResolvedAddress contains the actual resolved address value | [optional] 
**message** | **str** |  | [optional] 
**phase** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.execution_engine_v1prealpha1_status import ExecutionEngineV1prealpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of ExecutionEngineV1prealpha1Status from a JSON string
execution_engine_v1prealpha1_status_instance = ExecutionEngineV1prealpha1Status.from_json(json)
# print the JSON string representation of the object
print(ExecutionEngineV1prealpha1Status.to_json())

# convert the object into a dict
execution_engine_v1prealpha1_status_dict = execution_engine_v1prealpha1_status_instance.to_dict()
# create an instance of ExecutionEngineV1prealpha1Status from a dict
execution_engine_v1prealpha1_status_from_dict = ExecutionEngineV1prealpha1Status.from_dict(execution_engine_v1prealpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


