# A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef

SecretKeySelector selects a key of a Secret.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key** | **str** | The key of the secret to select from.  Must be a valid secret key. | 
**name** | **str** | Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names | [optional] [default to '']
**optional** | **bool** | Specify whether the Secret or its key must be defined | [optional] 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_spec_address_value_from_secret_key_ref import A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef from a JSON string
a2_a_server_v1prealpha1_spec_address_value_from_secret_key_ref_instance = A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_spec_address_value_from_secret_key_ref_dict = a2_a_server_v1prealpha1_spec_address_value_from_secret_key_ref_instance.to_dict()
# create an instance of A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef from a dict
a2_a_server_v1prealpha1_spec_address_value_from_secret_key_ref_from_dict = A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef.from_dict(a2_a_server_v1prealpha1_spec_address_value_from_secret_key_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


