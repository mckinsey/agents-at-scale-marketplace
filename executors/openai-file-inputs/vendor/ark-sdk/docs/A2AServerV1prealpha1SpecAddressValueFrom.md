# A2AServerV1prealpha1SpecAddressValueFrom


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config_map_key_ref** | [**A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef**](A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef.md) |  | [optional] 
**secret_key_ref** | [**A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef**](A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef.md) |  | [optional] 
**service_ref** | [**A2AServerV1prealpha1SpecAddressValueFromServiceRef**](A2AServerV1prealpha1SpecAddressValueFromServiceRef.md) |  | [optional] 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_spec_address_value_from import A2AServerV1prealpha1SpecAddressValueFrom

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1SpecAddressValueFrom from a JSON string
a2_a_server_v1prealpha1_spec_address_value_from_instance = A2AServerV1prealpha1SpecAddressValueFrom.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1SpecAddressValueFrom.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_spec_address_value_from_dict = a2_a_server_v1prealpha1_spec_address_value_from_instance.to_dict()
# create an instance of A2AServerV1prealpha1SpecAddressValueFrom from a dict
a2_a_server_v1prealpha1_spec_address_value_from_from_dict = A2AServerV1prealpha1SpecAddressValueFrom.from_dict(a2_a_server_v1prealpha1_spec_address_value_from_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


