# A2ATaskV1alpha1StatusHistoryInner

A2ATaskMessage represents messages exchanged during A2A task execution. Messages form the conversation history between user, agent, and system.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message_id** | **str** | MessageID is the unique identifier for this message from the A2A protocol. | [optional] 
**metadata** | **object** | Metadata contains additional key-value pairs for this message. | [optional] 
**parts** | [**List[A2ATaskV1alpha1StatusArtifactsInnerPartsInner]**](A2ATaskV1alpha1StatusArtifactsInnerPartsInner.md) | Parts contains the message content as one or more parts. | 
**role** | **str** | Role identifies the message sender: \&quot;user\&quot;, \&quot;agent\&quot;, or \&quot;system\&quot;. | 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_status_history_inner import A2ATaskV1alpha1StatusHistoryInner

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1StatusHistoryInner from a JSON string
a2_a_task_v1alpha1_status_history_inner_instance = A2ATaskV1alpha1StatusHistoryInner.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1StatusHistoryInner.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_status_history_inner_dict = a2_a_task_v1alpha1_status_history_inner_instance.to_dict()
# create an instance of A2ATaskV1alpha1StatusHistoryInner from a dict
a2_a_task_v1alpha1_status_history_inner_from_dict = A2ATaskV1alpha1StatusHistoryInner.from_dict(a2_a_task_v1alpha1_status_history_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


