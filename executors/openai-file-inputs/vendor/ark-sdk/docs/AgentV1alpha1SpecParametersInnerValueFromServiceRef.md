# AgentV1alpha1SpecParametersInnerValueFromServiceRef


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the service | 
**namespace** | **str** | Namespace of the service. Defaults to the namespace as the resource. | [optional] 
**path** | **str** | Path component of the service URL. For anthropic models might be &#39;v1&#39;, for gemini might be &#39;v1beta/openai&#39;, for MCP servers often will be &#39;mcp&#39; or &#39;sse&#39;. | [optional] 
**port** | **str** | Port name to use. If not specified, uses the service&#39;s only port or first port. | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_parameters_inner_value_from_service_ref import AgentV1alpha1SpecParametersInnerValueFromServiceRef

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecParametersInnerValueFromServiceRef from a JSON string
agent_v1alpha1_spec_parameters_inner_value_from_service_ref_instance = AgentV1alpha1SpecParametersInnerValueFromServiceRef.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecParametersInnerValueFromServiceRef.to_json())

# convert the object into a dict
agent_v1alpha1_spec_parameters_inner_value_from_service_ref_dict = agent_v1alpha1_spec_parameters_inner_value_from_service_ref_instance.to_dict()
# create an instance of AgentV1alpha1SpecParametersInnerValueFromServiceRef from a dict
agent_v1alpha1_spec_parameters_inner_value_from_service_ref_from_dict = AgentV1alpha1SpecParametersInnerValueFromServiceRef.from_dict(agent_v1alpha1_spec_parameters_inner_value_from_service_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


