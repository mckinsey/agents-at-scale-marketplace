# QueryV1alpha1StatusResponse

Response defines a response from a query target.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**a2a** | [**QueryV1alpha1StatusResponseA2a**](QueryV1alpha1StatusResponseA2a.md) |  | [optional] 
**content** | **str** |  | [optional] 
**phase** | **str** |  | [optional] 
**raw** | **str** |  | [optional] 
**target** | [**QueryV1alpha1SpecTarget**](QueryV1alpha1SpecTarget.md) |  | [optional] 

## Example

```python
from ark_sdk.models.query_v1alpha1_status_response import QueryV1alpha1StatusResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QueryV1alpha1StatusResponse from a JSON string
query_v1alpha1_status_response_instance = QueryV1alpha1StatusResponse.from_json(json)
# print the JSON string representation of the object
print(QueryV1alpha1StatusResponse.to_json())

# convert the object into a dict
query_v1alpha1_status_response_dict = query_v1alpha1_status_response_instance.to_dict()
# create an instance of QueryV1alpha1StatusResponse from a dict
query_v1alpha1_status_response_from_dict = QueryV1alpha1StatusResponse.from_dict(query_v1alpha1_status_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


