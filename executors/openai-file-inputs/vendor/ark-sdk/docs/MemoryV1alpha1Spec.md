# MemoryV1alpha1Spec

MemorySpec defines the desired state of Memory.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**address** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) | Headers contains HTTP headers to include in memory API requests | [optional] 

## Example

```python
from ark_sdk.models.memory_v1alpha1_spec import MemoryV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of MemoryV1alpha1Spec from a JSON string
memory_v1alpha1_spec_instance = MemoryV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(MemoryV1alpha1Spec.to_json())

# convert the object into a dict
memory_v1alpha1_spec_dict = memory_v1alpha1_spec_instance.to_dict()
# create an instance of MemoryV1alpha1Spec from a dict
memory_v1alpha1_spec_from_dict = MemoryV1alpha1Spec.from_dict(memory_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


