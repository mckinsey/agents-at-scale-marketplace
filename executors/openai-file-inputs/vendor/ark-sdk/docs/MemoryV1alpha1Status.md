# MemoryV1alpha1Status

MemoryStatus defines the observed state of Memory.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**last_resolved_address** | **str** | LastResolvedAddress contains the last resolved address value for reference | [optional] 
**message** | **str** | Message provides additional information about the current status | [optional] 
**phase** | **str** | Phase represents the current state of the memory | [optional] 

## Example

```python
from ark_sdk.models.memory_v1alpha1_status import MemoryV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of MemoryV1alpha1Status from a JSON string
memory_v1alpha1_status_instance = MemoryV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(MemoryV1alpha1Status.to_json())

# convert the object into a dict
memory_v1alpha1_status_dict = memory_v1alpha1_status_instance.to_dict()
# create an instance of MemoryV1alpha1Status from a dict
memory_v1alpha1_status_from_dict = MemoryV1alpha1Status.from_dict(memory_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


