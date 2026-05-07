# ExecutionEngineV1prealpha1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_version** | **str** | APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources | [optional] 
**kind** | **str** | Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds | [optional] 
**metadata** | **object** |  | [optional] 
**spec** | [**ExecutionEngineV1prealpha1Spec**](ExecutionEngineV1prealpha1Spec.md) |  | [optional] 
**status** | [**ExecutionEngineV1prealpha1Status**](ExecutionEngineV1prealpha1Status.md) |  | [optional] 

## Example

```python
from ark_sdk.models.execution_engine_v1prealpha1 import ExecutionEngineV1prealpha1

# TODO update the JSON string below
json = "{}"
# create an instance of ExecutionEngineV1prealpha1 from a JSON string
execution_engine_v1prealpha1_instance = ExecutionEngineV1prealpha1.from_json(json)
# print the JSON string representation of the object
print(ExecutionEngineV1prealpha1.to_json())

# convert the object into a dict
execution_engine_v1prealpha1_dict = execution_engine_v1prealpha1_instance.to_dict()
# create an instance of ExecutionEngineV1prealpha1 from a dict
execution_engine_v1prealpha1_from_dict = ExecutionEngineV1prealpha1.from_dict(execution_engine_v1prealpha1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


