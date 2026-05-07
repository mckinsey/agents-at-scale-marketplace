# ListEvaluatorsV1alpha1200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[EvaluatorV1alpha1]**](EvaluatorV1alpha1.md) |  | [optional] 

## Example

```python
from ark_sdk.models.list_evaluators_v1alpha1200_response import ListEvaluatorsV1alpha1200Response

# TODO update the JSON string below
json = "{}"
# create an instance of ListEvaluatorsV1alpha1200Response from a JSON string
list_evaluators_v1alpha1200_response_instance = ListEvaluatorsV1alpha1200Response.from_json(json)
# print the JSON string representation of the object
print(ListEvaluatorsV1alpha1200Response.to_json())

# convert the object into a dict
list_evaluators_v1alpha1200_response_dict = list_evaluators_v1alpha1200_response_instance.to_dict()
# create an instance of ListEvaluatorsV1alpha1200Response from a dict
list_evaluators_v1alpha1200_response_from_dict = ListEvaluatorsV1alpha1200Response.from_dict(list_evaluators_v1alpha1200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


