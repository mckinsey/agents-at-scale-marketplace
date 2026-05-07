# AgentV1alpha1SpecParametersInnerValueFrom

Reference to external sources (mutually exclusive with value)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config_map_key_ref** | [**A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef**](A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef.md) |  | [optional] 
**query_parameter_ref** | [**A2AServerV1prealpha1SpecHeadersInnerValueValueFromQueryParameterRef**](A2AServerV1prealpha1SpecHeadersInnerValueValueFromQueryParameterRef.md) |  | [optional] 
**secret_key_ref** | [**A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef**](A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef.md) |  | [optional] 
**service_ref** | [**AgentV1alpha1SpecParametersInnerValueFromServiceRef**](AgentV1alpha1SpecParametersInnerValueFromServiceRef.md) |  | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_parameters_inner_value_from import AgentV1alpha1SpecParametersInnerValueFrom

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecParametersInnerValueFrom from a JSON string
agent_v1alpha1_spec_parameters_inner_value_from_instance = AgentV1alpha1SpecParametersInnerValueFrom.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecParametersInnerValueFrom.to_json())

# convert the object into a dict
agent_v1alpha1_spec_parameters_inner_value_from_dict = agent_v1alpha1_spec_parameters_inner_value_from_instance.to_dict()
# create an instance of AgentV1alpha1SpecParametersInnerValueFrom from a dict
agent_v1alpha1_spec_parameters_inner_value_from_from_dict = AgentV1alpha1SpecParametersInnerValueFrom.from_dict(agent_v1alpha1_spec_parameters_inner_value_from_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


