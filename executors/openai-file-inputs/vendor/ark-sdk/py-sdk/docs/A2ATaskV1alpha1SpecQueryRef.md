# A2ATaskV1alpha1SpecQueryRef

QueryRef references the Query that created this A2A task.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**namespace** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_spec_query_ref import A2ATaskV1alpha1SpecQueryRef

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1SpecQueryRef from a JSON string
a2_a_task_v1alpha1_spec_query_ref_instance = A2ATaskV1alpha1SpecQueryRef.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1SpecQueryRef.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_spec_query_ref_dict = a2_a_task_v1alpha1_spec_query_ref_instance.to_dict()
# create an instance of A2ATaskV1alpha1SpecQueryRef from a dict
a2_a_task_v1alpha1_spec_query_ref_from_dict = A2ATaskV1alpha1SpecQueryRef.from_dict(a2_a_task_v1alpha1_spec_query_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


