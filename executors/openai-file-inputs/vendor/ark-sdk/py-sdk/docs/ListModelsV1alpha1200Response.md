# ListModelsV1alpha1200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[ModelV1alpha1]**](ModelV1alpha1.md) |  | [optional] 

## Example

```python
from ark_sdk.models.list_models_v1alpha1200_response import ListModelsV1alpha1200Response

# TODO update the JSON string below
json = "{}"
# create an instance of ListModelsV1alpha1200Response from a JSON string
list_models_v1alpha1200_response_instance = ListModelsV1alpha1200Response.from_json(json)
# print the JSON string representation of the object
print(ListModelsV1alpha1200Response.to_json())

# convert the object into a dict
list_models_v1alpha1200_response_dict = list_models_v1alpha1200_response_instance.to_dict()
# create an instance of ListModelsV1alpha1200Response from a dict
list_models_v1alpha1200_response_from_dict = ListModelsV1alpha1200Response.from_dict(list_models_v1alpha1200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


