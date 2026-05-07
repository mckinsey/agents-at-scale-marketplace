# A2AServerV1prealpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of the A2A server&#39;s state | [optional] 
**last_resolved_address** | **str** | LastResolvedAddress contains the last resolved address value | [optional] 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_status import A2AServerV1prealpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1Status from a JSON string
a2_a_server_v1prealpha1_status_instance = A2AServerV1prealpha1Status.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1Status.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_status_dict = a2_a_server_v1prealpha1_status_instance.to_dict()
# create an instance of A2AServerV1prealpha1Status from a dict
a2_a_server_v1prealpha1_status_from_dict = A2AServerV1prealpha1Status.from_dict(a2_a_server_v1prealpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


