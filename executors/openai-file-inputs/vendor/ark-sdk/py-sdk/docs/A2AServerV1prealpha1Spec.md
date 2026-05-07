# A2AServerV1prealpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**address** | [**A2AServerV1prealpha1SpecAddress**](A2AServerV1prealpha1SpecAddress.md) |  | 
**description** | **str** | Description of the A2A server | [optional] 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) | Headers for authentication and other metadata | [optional] 
**poll_interval** | **str** |  | [optional] [default to '1m']
**timeout** | **str** | Timeout for A2A agent execution (e.g., \&quot;30s\&quot;, \&quot;5m\&quot;, \&quot;1h\&quot;) | [optional] [default to '5m']

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_spec import A2AServerV1prealpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1Spec from a JSON string
a2_a_server_v1prealpha1_spec_instance = A2AServerV1prealpha1Spec.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1Spec.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_spec_dict = a2_a_server_v1prealpha1_spec_instance.to_dict()
# create an instance of A2AServerV1prealpha1Spec from a dict
a2_a_server_v1prealpha1_spec_from_dict = A2AServerV1prealpha1Spec.from_dict(a2_a_server_v1prealpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


