# MCPServerV1alpha1SpecAddress

ValueSource represents a source for a configuration value

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | [optional] 
**value_from** | [**AgentV1alpha1SpecToolsInnerFunctionsInnerValueFrom**](AgentV1alpha1SpecToolsInnerFunctionsInnerValueFrom.md) |  | [optional] 

## Example

```python
from ark_sdk.models.mcp_server_v1alpha1_spec_address import MCPServerV1alpha1SpecAddress

# TODO update the JSON string below
json = "{}"
# create an instance of MCPServerV1alpha1SpecAddress from a JSON string
mcp_server_v1alpha1_spec_address_instance = MCPServerV1alpha1SpecAddress.from_json(json)
# print the JSON string representation of the object
print(MCPServerV1alpha1SpecAddress.to_json())

# convert the object into a dict
mcp_server_v1alpha1_spec_address_dict = mcp_server_v1alpha1_spec_address_instance.to_dict()
# create an instance of MCPServerV1alpha1SpecAddress from a dict
mcp_server_v1alpha1_spec_address_from_dict = MCPServerV1alpha1SpecAddress.from_dict(mcp_server_v1alpha1_spec_address_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


