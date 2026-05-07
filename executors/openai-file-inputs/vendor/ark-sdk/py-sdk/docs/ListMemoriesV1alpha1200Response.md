# ListMemoriesV1alpha1200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[MemoryV1alpha1]**](MemoryV1alpha1.md) |  | [optional] 

## Example

```python
from ark_sdk.models.list_memories_v1alpha1200_response import ListMemoriesV1alpha1200Response

# TODO update the JSON string below
json = "{}"
# create an instance of ListMemoriesV1alpha1200Response from a JSON string
list_memories_v1alpha1200_response_instance = ListMemoriesV1alpha1200Response.from_json(json)
# print the JSON string representation of the object
print(ListMemoriesV1alpha1200Response.to_json())

# convert the object into a dict
list_memories_v1alpha1200_response_dict = list_memories_v1alpha1200_response_instance.to_dict()
# create an instance of ListMemoriesV1alpha1200Response from a dict
list_memories_v1alpha1200_response_from_dict = ListMemoriesV1alpha1200Response.from_dict(list_memories_v1alpha1200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


