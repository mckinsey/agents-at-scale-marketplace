# QueryV1alpha1StatusResponsesInner

Response defines a response from a query target.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**a2a** | [**QueryV1alpha1StatusResponsesInnerA2a**](QueryV1alpha1StatusResponsesInnerA2a.md) |  | [optional] 
**content** | **str** |  | [optional] 
**phase** | **str** |  | [optional] 
**raw** | **str** |  | [optional] 
**target** | [**QueryV1alpha1SpecTargetsInner**](QueryV1alpha1SpecTargetsInner.md) |  | [optional] 

## Example

```python
from ark_sdk.models.query_v1alpha1_status_responses_inner import QueryV1alpha1StatusResponsesInner

# TODO update the JSON string below
json = "{}"
# create an instance of QueryV1alpha1StatusResponsesInner from a JSON string
query_v1alpha1_status_responses_inner_instance = QueryV1alpha1StatusResponsesInner.from_json(json)
# print the JSON string representation of the object
print(QueryV1alpha1StatusResponsesInner.to_json())

# convert the object into a dict
query_v1alpha1_status_responses_inner_dict = query_v1alpha1_status_responses_inner_instance.to_dict()
# create an instance of QueryV1alpha1StatusResponsesInner from a dict
query_v1alpha1_status_responses_inner_from_dict = QueryV1alpha1StatusResponsesInner.from_dict(query_v1alpha1_status_responses_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


