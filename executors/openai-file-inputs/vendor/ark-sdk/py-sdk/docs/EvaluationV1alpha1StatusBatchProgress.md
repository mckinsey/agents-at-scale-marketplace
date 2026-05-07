# EvaluationV1alpha1StatusBatchProgress

Batch evaluation progress (only set for batch type evaluations)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**child_evaluations** | [**List[EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner]**](EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner.md) | List of child evaluation names and their status | [optional] 
**completed** | **int** | Number of child evaluations completed | [optional] 
**failed** | **int** | Number of child evaluations that failed | [optional] 
**running** | **int** | Number of child evaluations currently running | [optional] 
**total** | **int** | Total number of child evaluations created | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_status_batch_progress import EvaluationV1alpha1StatusBatchProgress

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1StatusBatchProgress from a JSON string
evaluation_v1alpha1_status_batch_progress_instance = EvaluationV1alpha1StatusBatchProgress.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1StatusBatchProgress.to_json())

# convert the object into a dict
evaluation_v1alpha1_status_batch_progress_dict = evaluation_v1alpha1_status_batch_progress_instance.to_dict()
# create an instance of EvaluationV1alpha1StatusBatchProgress from a dict
evaluation_v1alpha1_status_batch_progress_from_dict = EvaluationV1alpha1StatusBatchProgress.from_dict(evaluation_v1alpha1_status_batch_progress_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


