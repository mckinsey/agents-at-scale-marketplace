# EvaluationV1alpha1Status

EvaluationStatus defines the observed state of Evaluation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**batch_progress** | [**EvaluationV1alpha1StatusBatchProgress**](EvaluationV1alpha1StatusBatchProgress.md) |  | [optional] 
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of an evaluation&#39;s state | [optional] 
**duration** | **str** |  | [optional] 
**message** | **str** |  | [optional] 
**passed** | **bool** |  | [optional] 
**phase** | **str** |  | [optional] 
**score** | **str** |  | [optional] 
**token_usage** | [**EvaluationV1alpha1StatusTokenUsage**](EvaluationV1alpha1StatusTokenUsage.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_status import EvaluationV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1Status from a JSON string
evaluation_v1alpha1_status_instance = EvaluationV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1Status.to_json())

# convert the object into a dict
evaluation_v1alpha1_status_dict = evaluation_v1alpha1_status_instance.to_dict()
# create an instance of EvaluationV1alpha1Status from a dict
evaluation_v1alpha1_status_from_dict = EvaluationV1alpha1Status.from_dict(evaluation_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


