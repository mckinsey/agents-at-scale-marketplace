# ToolV1alpha1SpecBuiltin

Builtin-specific configuration for builtin tools. This field is required only if Type = \"builtin\".

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the Builtin being referenced. This must be a non-empty string. | 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec_builtin import ToolV1alpha1SpecBuiltin

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1SpecBuiltin from a JSON string
tool_v1alpha1_spec_builtin_instance = ToolV1alpha1SpecBuiltin.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1SpecBuiltin.to_json())

# convert the object into a dict
tool_v1alpha1_spec_builtin_dict = tool_v1alpha1_spec_builtin_instance.to_dict()
# create an instance of ToolV1alpha1SpecBuiltin from a dict
tool_v1alpha1_spec_builtin_from_dict = ToolV1alpha1SpecBuiltin.from_dict(tool_v1alpha1_spec_builtin_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


