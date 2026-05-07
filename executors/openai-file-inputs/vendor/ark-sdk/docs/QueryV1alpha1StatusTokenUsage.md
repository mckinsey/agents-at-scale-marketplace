# QueryV1alpha1StatusTokenUsage


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completion_tokens** | **int** |  | [optional] 
**prompt_tokens** | **int** |  | [optional] 
**total_tokens** | **int** |  | [optional] 

## Example

```python
from ark_sdk.models.query_v1alpha1_status_token_usage import QueryV1alpha1StatusTokenUsage

# TODO update the JSON string below
json = "{}"
# create an instance of QueryV1alpha1StatusTokenUsage from a JSON string
query_v1alpha1_status_token_usage_instance = QueryV1alpha1StatusTokenUsage.from_json(json)
# print the JSON string representation of the object
print(QueryV1alpha1StatusTokenUsage.to_json())

# convert the object into a dict
query_v1alpha1_status_token_usage_dict = query_v1alpha1_status_token_usage_instance.to_dict()
# create an instance of QueryV1alpha1StatusTokenUsage from a dict
query_v1alpha1_status_token_usage_from_dict = QueryV1alpha1StatusTokenUsage.from_dict(query_v1alpha1_status_token_usage_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


