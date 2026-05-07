# A2ATaskV1alpha1SpecA2aServerRef

A2AServerRef references the A2AServer to poll for task status updates.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the A2AServer resource. | 
**namespace** | **str** | Namespace where the A2AServer resource is located. If empty, defaults to the same namespace as the A2ATask. | [optional] 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_spec_a2a_server_ref import A2ATaskV1alpha1SpecA2aServerRef

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1SpecA2aServerRef from a JSON string
a2_a_task_v1alpha1_spec_a2a_server_ref_instance = A2ATaskV1alpha1SpecA2aServerRef.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1SpecA2aServerRef.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_spec_a2a_server_ref_dict = a2_a_task_v1alpha1_spec_a2a_server_ref_instance.to_dict()
# create an instance of A2ATaskV1alpha1SpecA2aServerRef from a dict
a2_a_task_v1alpha1_spec_a2a_server_ref_from_dict = A2ATaskV1alpha1SpecA2aServerRef.from_dict(a2_a_task_v1alpha1_spec_a2a_server_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


