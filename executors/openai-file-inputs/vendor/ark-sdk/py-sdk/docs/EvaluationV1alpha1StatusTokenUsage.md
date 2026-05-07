# EvaluationV1alpha1StatusTokenUsage


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completion_tokens** | **int** |  | [optional] 
**prompt_tokens** | **int** |  | [optional] 
**total_tokens** | **int** |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_status_token_usage import EvaluationV1alpha1StatusTokenUsage

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1StatusTokenUsage from a JSON string
evaluation_v1alpha1_status_token_usage_instance = EvaluationV1alpha1StatusTokenUsage.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1StatusTokenUsage.to_json())

# convert the object into a dict
evaluation_v1alpha1_status_token_usage_dict = evaluation_v1alpha1_status_token_usage_instance.to_dict()
# create an instance of EvaluationV1alpha1StatusTokenUsage from a dict
evaluation_v1alpha1_status_token_usage_from_dict = EvaluationV1alpha1StatusTokenUsage.from_dict(evaluation_v1alpha1_status_token_usage_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


