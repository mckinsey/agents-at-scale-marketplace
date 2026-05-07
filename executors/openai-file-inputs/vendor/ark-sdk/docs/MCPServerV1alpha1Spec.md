# MCPServerV1alpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**address** | [**MCPServerV1alpha1SpecAddress**](MCPServerV1alpha1SpecAddress.md) |  | 
**description** | **str** |  | [optional] 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) |  | [optional] 
**poll_interval** | **str** |  | [optional] [default to '1m']
**timeout** | **str** | Timeout specifies the maximum duration for MCP tool calls to this server. Use this to support long-running operations (e.g., \&quot;5m\&quot;, \&quot;10m\&quot;, \&quot;30m\&quot;). Defaults to \&quot;30s\&quot; if not specified. | [optional] [default to '30s']
**transport** | **str** |  | [default to 'http']

## Example

```python
from ark_sdk.models.mcp_server_v1alpha1_spec import MCPServerV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of MCPServerV1alpha1Spec from a JSON string
mcp_server_v1alpha1_spec_instance = MCPServerV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(MCPServerV1alpha1Spec.to_json())

# convert the object into a dict
mcp_server_v1alpha1_spec_dict = mcp_server_v1alpha1_spec_instance.to_dict()
# create an instance of MCPServerV1alpha1Spec from a dict
mcp_server_v1alpha1_spec_from_dict = MCPServerV1alpha1Spec.from_dict(mcp_server_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


