# A2AServerV1prealpha1SpecAddress

Address specifies how to reach the A2A server

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | [optional] 
**value_from** | [**A2AServerV1prealpha1SpecAddressValueFrom**](A2AServerV1prealpha1SpecAddressValueFrom.md) |  | [optional] 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_spec_address import A2AServerV1prealpha1SpecAddress

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1SpecAddress from a JSON string
a2_a_server_v1prealpha1_spec_address_instance = A2AServerV1prealpha1SpecAddress.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1SpecAddress.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_spec_address_dict = a2_a_server_v1prealpha1_spec_address_instance.to_dict()
# create an instance of A2AServerV1prealpha1SpecAddress from a dict
a2_a_server_v1prealpha1_spec_address_from_dict = A2AServerV1prealpha1SpecAddress.from_dict(a2_a_server_v1prealpha1_spec_address_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


