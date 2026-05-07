# ToolV1alpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message** | **str** |  | [optional] 
**state** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.tool_v1alpha1_status import ToolV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1Status from a JSON string
tool_v1alpha1_status_instance = ToolV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1Status.to_json())

# convert the object into a dict
tool_v1alpha1_status_dict = tool_v1alpha1_status_instance.to_dict()
# create an instance of ToolV1alpha1Status from a dict
tool_v1alpha1_status_from_dict = ToolV1alpha1Status.from_dict(tool_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


