# A2ATaskV1alpha1Spec

A2ATaskSpec defines the desired state of an A2ATask. Links the task to its originating query and captures task parameters.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**a2a_server_ref** | [**A2ATaskV1alpha1SpecA2aServerRef**](A2ATaskV1alpha1SpecA2aServerRef.md) |  | 
**agent_ref** | [**A2ATaskV1alpha1SpecAgentRef**](A2ATaskV1alpha1SpecAgentRef.md) |  | 
**context_id** | **str** | ContextID links this task to an A2A conversation context for stateful interactions. | [optional] 
**input** | **str** | Input contains the user&#39;s input that initiated this task. | [optional] 
**parameters** | **object** | Parameters contains additional key-value parameters for task execution. | [optional] 
**poll_interval** | **str** | PollInterval specifies how frequently to check the A2A server for task status updates. | [optional] [default to '5s']
**priority** | **int** | Priority determines task execution order (higher values execute first). | [optional] [default to 0]
**query_ref** | [**A2ATaskV1alpha1SpecQueryRef**](A2ATaskV1alpha1SpecQueryRef.md) |  | 
**task_id** | **str** | TaskID is the unique identifier from the A2A protocol. | 
**timeout** | **str** | Timeout specifies how long we will poll the A2A server for task completion before timing out. If the task has not reached a terminal state (completed, failed, cancelled) within this duration, it will be marked as failed. | [optional] [default to '12h']
**ttl** | **str** | TTL (time to live) specifies how long to keep this A2ATask resource in the system after completion. After this duration, the resource may be automatically deleted. | [optional] [default to '720h']

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_spec import A2ATaskV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1Spec from a JSON string
a2_a_task_v1alpha1_spec_instance = A2ATaskV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1Spec.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_spec_dict = a2_a_task_v1alpha1_spec_instance.to_dict()
# create an instance of A2ATaskV1alpha1Spec from a dict
a2_a_task_v1alpha1_spec_from_dict = A2ATaskV1alpha1Spec.from_dict(a2_a_task_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


