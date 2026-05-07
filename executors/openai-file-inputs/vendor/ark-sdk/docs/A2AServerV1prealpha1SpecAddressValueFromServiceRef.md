# A2AServerV1prealpha1SpecAddressValueFromServiceRef


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the service | 
**namespace** | **str** | Namespace of the service. Defaults to the namespace as the resource. | [optional] 
**path** | **str** | Optional path to append to the service address. For models might be &#39;v1&#39;, for gemini might be &#39;v1beta/openai&#39;, for mcp servers might be &#39;mcp&#39;. | [optional] 
**port** | **str** | Port name to use. If not specified, uses the service&#39;s only port or first port. | [optional] 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_spec_address_value_from_service_ref import A2AServerV1prealpha1SpecAddressValueFromServiceRef

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1SpecAddressValueFromServiceRef from a JSON string
a2_a_server_v1prealpha1_spec_address_value_from_service_ref_instance = A2AServerV1prealpha1SpecAddressValueFromServiceRef.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1SpecAddressValueFromServiceRef.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_spec_address_value_from_service_ref_dict = a2_a_server_v1prealpha1_spec_address_value_from_service_ref_instance.to_dict()
# create an instance of A2AServerV1prealpha1SpecAddressValueFromServiceRef from a dict
a2_a_server_v1prealpha1_spec_address_value_from_service_ref_from_dict = A2AServerV1prealpha1SpecAddressValueFromServiceRef.from_dict(a2_a_server_v1prealpha1_spec_address_value_from_service_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


