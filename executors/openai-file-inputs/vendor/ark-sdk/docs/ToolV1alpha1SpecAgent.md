# ToolV1alpha1SpecAgent

Agent-specific configuration for agent tools. This field is required only if Type = \"agent\".

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the Agent being referenced. This must be a non-empty string. | 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec_agent import ToolV1alpha1SpecAgent

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1SpecAgent from a JSON string
tool_v1alpha1_spec_agent_instance = ToolV1alpha1SpecAgent.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1SpecAgent.to_json())

# convert the object into a dict
tool_v1alpha1_spec_agent_dict = tool_v1alpha1_spec_agent_instance.to_dict()
# create an instance of ToolV1alpha1SpecAgent from a dict
tool_v1alpha1_spec_agent_from_dict = ToolV1alpha1SpecAgent.from_dict(tool_v1alpha1_spec_agent_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


