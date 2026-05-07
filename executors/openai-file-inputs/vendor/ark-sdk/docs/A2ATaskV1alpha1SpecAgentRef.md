# A2ATaskV1alpha1SpecAgentRef

AgentRef references the agent executing this task.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the Agent resource. | [optional] 
**namespace** | **str** | Namespace where the Agent resource is located. If empty, defaults to the same namespace as the A2ATask. | [optional] 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_spec_agent_ref import A2ATaskV1alpha1SpecAgentRef

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1SpecAgentRef from a JSON string
a2_a_task_v1alpha1_spec_agent_ref_instance = A2ATaskV1alpha1SpecAgentRef.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1SpecAgentRef.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_spec_agent_ref_dict = a2_a_task_v1alpha1_spec_agent_ref_instance.to_dict()
# create an instance of A2ATaskV1alpha1SpecAgentRef from a dict
a2_a_task_v1alpha1_spec_agent_ref_from_dict = A2ATaskV1alpha1SpecAgentRef.from_dict(a2_a_task_v1alpha1_spec_agent_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


