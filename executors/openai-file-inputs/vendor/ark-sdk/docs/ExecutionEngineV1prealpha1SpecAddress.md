# ExecutionEngineV1prealpha1SpecAddress

Address specifies how to reach the execution engine

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | [optional] 
**value_from** | [**A2AServerV1prealpha1SpecAddressValueFrom**](A2AServerV1prealpha1SpecAddressValueFrom.md) |  | [optional] 

## Example

```python
from ark_sdk.models.execution_engine_v1prealpha1_spec_address import ExecutionEngineV1prealpha1SpecAddress

# TODO update the JSON string below
json = "{}"
# create an instance of ExecutionEngineV1prealpha1SpecAddress from a JSON string
execution_engine_v1prealpha1_spec_address_instance = ExecutionEngineV1prealpha1SpecAddress.from_json(json)
# print the JSON string representation of the object
print(ExecutionEngineV1prealpha1SpecAddress.to_json())

# convert the object into a dict
execution_engine_v1prealpha1_spec_address_dict = execution_engine_v1prealpha1_spec_address_instance.to_dict()
# create an instance of ExecutionEngineV1prealpha1SpecAddress from a dict
execution_engine_v1prealpha1_spec_address_from_dict = ExecutionEngineV1prealpha1SpecAddress.from_dict(execution_engine_v1prealpha1_spec_address_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


