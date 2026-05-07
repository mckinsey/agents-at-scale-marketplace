# MCPServerV1alpha1Status

MCPServerStatus defines the observed state of MCPServer

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of the MCP server&#39;s state | [optional] 
**resolved_address** | **str** | ResolvedAddress contains the actual resolved address value | [optional] 
**tool_count** | **int** | ToolCount represents the number of tools discovered from this MCP server | [optional] 

## Example

```python
from ark_sdk.models.mcp_server_v1alpha1_status import MCPServerV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of MCPServerV1alpha1Status from a JSON string
mcp_server_v1alpha1_status_instance = MCPServerV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(MCPServerV1alpha1Status.to_json())

# convert the object into a dict
mcp_server_v1alpha1_status_dict = mcp_server_v1alpha1_status_instance.to_dict()
# create an instance of MCPServerV1alpha1Status from a dict
mcp_server_v1alpha1_status_from_dict = MCPServerV1alpha1Status.from_dict(mcp_server_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


