# ToolV1alpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent** | [**ToolV1alpha1SpecAgent**](ToolV1alpha1SpecAgent.md) |  | [optional] 
**annotations** | [**ToolV1alpha1SpecAnnotations**](ToolV1alpha1SpecAnnotations.md) |  | [optional] 
**builtin** | [**ToolV1alpha1SpecBuiltin**](ToolV1alpha1SpecBuiltin.md) |  | [optional] 
**description** | **str** | Tool description | [optional] 
**http** | [**ToolV1alpha1SpecHttp**](ToolV1alpha1SpecHttp.md) |  | [optional] 
**input_schema** | **object** | Input schema for the tool | [optional] 
**mcp** | [**ToolV1alpha1SpecMcp**](ToolV1alpha1SpecMcp.md) |  | [optional] 
**team** | [**ToolV1alpha1SpecTeam**](ToolV1alpha1SpecTeam.md) |  | [optional] 
**type** | **str** |  | 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec import ToolV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1Spec from a JSON string
tool_v1alpha1_spec_instance = ToolV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1Spec.to_json())

# convert the object into a dict
tool_v1alpha1_spec_dict = tool_v1alpha1_spec_instance.to_dict()
# create an instance of ToolV1alpha1Spec from a dict
tool_v1alpha1_spec_from_dict = ToolV1alpha1Spec.from_dict(tool_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


