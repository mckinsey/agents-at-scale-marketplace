# QueryV1alpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of a query&#39;s state | [optional] 
**conversation_id** | **str** |  | [optional] 
**duration** | **str** |  | [optional] 
**phase** | **str** |  | [optional] [default to 'pending']
**response** | [**QueryV1alpha1StatusResponse**](QueryV1alpha1StatusResponse.md) |  | [optional] 
**token_usage** | [**QueryV1alpha1StatusTokenUsage**](QueryV1alpha1StatusTokenUsage.md) |  | [optional] 

## Example

```python
from ark_sdk.models.query_v1alpha1_status import QueryV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of QueryV1alpha1Status from a JSON string
query_v1alpha1_status_instance = QueryV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(QueryV1alpha1Status.to_json())

# convert the object into a dict
query_v1alpha1_status_dict = query_v1alpha1_status_instance.to_dict()
# create an instance of QueryV1alpha1Status from a dict
query_v1alpha1_status_from_dict = QueryV1alpha1Status.from_dict(query_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


