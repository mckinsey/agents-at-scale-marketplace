# A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef

Selects a key from a ConfigMap.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key** | **str** | The key to select. | 
**name** | **str** | Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names | [optional] [default to '']
**optional** | **bool** | Specify whether the ConfigMap or its key must be defined | [optional] 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_spec_address_value_from_config_map_key_ref import A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef from a JSON string
a2_a_server_v1prealpha1_spec_address_value_from_config_map_key_ref_instance = A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_spec_address_value_from_config_map_key_ref_dict = a2_a_server_v1prealpha1_spec_address_value_from_config_map_key_ref_instance.to_dict()
# create an instance of A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef from a dict
a2_a_server_v1prealpha1_spec_address_value_from_config_map_key_ref_from_dict = A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef.from_dict(a2_a_server_v1prealpha1_spec_address_value_from_config_map_key_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


