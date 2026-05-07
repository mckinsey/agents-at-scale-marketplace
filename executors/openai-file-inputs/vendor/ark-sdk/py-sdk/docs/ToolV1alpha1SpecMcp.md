# ToolV1alpha1SpecMcp

MCP-specific configuration for MCP server tools

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**mcp_server_ref** | [**ToolV1alpha1SpecMcpMcpServerRef**](ToolV1alpha1SpecMcpMcpServerRef.md) |  | 
**tool_name** | **str** |  | 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec_mcp import ToolV1alpha1SpecMcp

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1SpecMcp from a JSON string
tool_v1alpha1_spec_mcp_instance = ToolV1alpha1SpecMcp.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1SpecMcp.to_json())

# convert the object into a dict
tool_v1alpha1_spec_mcp_dict = tool_v1alpha1_spec_mcp_instance.to_dict()
# create an instance of ToolV1alpha1SpecMcp from a dict
tool_v1alpha1_spec_mcp_from_dict = ToolV1alpha1SpecMcp.from_dict(tool_v1alpha1_spec_mcp_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


