# AgentV1alpha1SpecParametersInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the parameter (used as template variable) | 
**value** | **str** | Direct value (mutually exclusive with valueFrom) | [optional] 
**value_from** | [**AgentV1alpha1SpecParametersInnerValueFrom**](AgentV1alpha1SpecParametersInnerValueFrom.md) |  | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_spec_parameters_inner import AgentV1alpha1SpecParametersInner

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1SpecParametersInner from a JSON string
agent_v1alpha1_spec_parameters_inner_instance = AgentV1alpha1SpecParametersInner.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1SpecParametersInner.to_json())

# convert the object into a dict
agent_v1alpha1_spec_parameters_inner_dict = agent_v1alpha1_spec_parameters_inner_instance.to_dict()
# create an instance of AgentV1alpha1SpecParametersInner from a dict
agent_v1alpha1_spec_parameters_inner_from_dict = AgentV1alpha1SpecParametersInner.from_dict(agent_v1alpha1_spec_parameters_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


