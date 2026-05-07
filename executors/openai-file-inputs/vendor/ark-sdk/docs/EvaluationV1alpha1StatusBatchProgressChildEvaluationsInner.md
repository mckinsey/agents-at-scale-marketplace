# EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner

ChildEvaluationStatus represents the status of a child evaluation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message** | **str** |  | [optional] 
**name** | **str** |  | 
**passed** | **bool** |  | [optional] 
**phase** | **str** |  | [optional] 
**score** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_status_batch_progress_child_evaluations_inner import EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner from a JSON string
evaluation_v1alpha1_status_batch_progress_child_evaluations_inner_instance = EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner.to_json())

# convert the object into a dict
evaluation_v1alpha1_status_batch_progress_child_evaluations_inner_dict = evaluation_v1alpha1_status_batch_progress_child_evaluations_inner_instance.to_dict()
# create an instance of EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner from a dict
evaluation_v1alpha1_status_batch_progress_child_evaluations_inner_from_dict = EvaluationV1alpha1StatusBatchProgressChildEvaluationsInner.from_dict(evaluation_v1alpha1_status_batch_progress_child_evaluations_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


