# QueryV1alpha1StatusResponsesInnerA2a

A2A contains optional A2A protocol metadata (contextId, taskId)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**context_id** | **str** | ContextID from the A2A protocol when the target is an A2A agent | [optional] 
**task_id** | **str** | TaskID from the A2A protocol when the target is an A2A agent and a task was created | [optional] 

## Example

```python
from ark_sdk.models.query_v1alpha1_status_responses_inner_a2a import QueryV1alpha1StatusResponsesInnerA2a

# TODO update the JSON string below
json = "{}"
# create an instance of QueryV1alpha1StatusResponsesInnerA2a from a JSON string
query_v1alpha1_status_responses_inner_a2a_instance = QueryV1alpha1StatusResponsesInnerA2a.from_json(json)
# print the JSON string representation of the object
print(QueryV1alpha1StatusResponsesInnerA2a.to_json())

# convert the object into a dict
query_v1alpha1_status_responses_inner_a2a_dict = query_v1alpha1_status_responses_inner_a2a_instance.to_dict()
# create an instance of QueryV1alpha1StatusResponsesInnerA2a from a dict
query_v1alpha1_status_responses_inner_a2a_from_dict = QueryV1alpha1StatusResponsesInnerA2a.from_dict(query_v1alpha1_status_responses_inner_a2a_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


