# A2ATaskV1alpha1Status

A2ATaskStatus defines the observed state of an A2ATask. Combines Kubernetes lifecycle tracking with A2A protocol task data.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**artifacts** | [**List[A2ATaskV1alpha1StatusArtifactsInner]**](A2ATaskV1alpha1StatusArtifactsInner.md) | Artifacts contains outputs produced by the A2A task execution. | [optional] 
**completion_time** | **str** | CompletionTime records when task execution finished (success or failure). | [optional] 
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of the task&#39;s state. The Completed condition indicates whether the task is no longer running. | [optional] 
**context_id** | **str** | ContextID links this task to a specific A2A conversation context. | [optional] 
**error** | **str** | Error contains the error message if the task failed. | [optional] 
**history** | [**List[A2ATaskV1alpha1StatusHistoryInner]**](A2ATaskV1alpha1StatusHistoryInner.md) | History contains the complete conversation from the A2A protocol. | [optional] 
**last_status_message** | [**A2ATaskV1alpha1StatusLastStatusMessage**](A2ATaskV1alpha1StatusLastStatusMessage.md) |  | [optional] 
**last_status_timestamp** | **str** | LastStatusTimestamp records when the protocol status was last updated (RFC3339 format). | [optional] 
**phase** | **str** | Phase indicates the current Kubernetes lifecycle stage of the task. Possible values: pending, assigned, running, input-required, auth-required, completed, failed, cancelled, unknown. | [optional] [default to 'pending']
**protocol_metadata** | **object** | ProtocolMetadata contains additional key-value pairs from the A2A protocol. | [optional] 
**protocol_state** | **str** | A2A Protocol fields (flattened from protocol.Task) ProtocolState indicates the current state in the A2A protocol. Possible values: submitted, working, input-required, completed, canceled, failed, rejected, auth-required, unknown. | [optional] 
**start_time** | **str** | StartTime records when task execution began. | [optional] 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_status import A2ATaskV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1Status from a JSON string
a2_a_task_v1alpha1_status_instance = A2ATaskV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1Status.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_status_dict = a2_a_task_v1alpha1_status_instance.to_dict()
# create an instance of A2ATaskV1alpha1Status from a dict
a2_a_task_v1alpha1_status_from_dict = A2ATaskV1alpha1Status.from_dict(a2_a_task_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


