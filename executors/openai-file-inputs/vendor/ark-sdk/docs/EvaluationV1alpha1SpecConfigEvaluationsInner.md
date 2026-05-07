# EvaluationV1alpha1SpecConfigEvaluationsInner

EvaluationRef references an evaluation to aggregate in batch type

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**namespace** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_evaluations_inner import EvaluationV1alpha1SpecConfigEvaluationsInner

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigEvaluationsInner from a JSON string
evaluation_v1alpha1_spec_config_evaluations_inner_instance = EvaluationV1alpha1SpecConfigEvaluationsInner.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigEvaluationsInner.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_evaluations_inner_dict = evaluation_v1alpha1_spec_config_evaluations_inner_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigEvaluationsInner from a dict
evaluation_v1alpha1_spec_config_evaluations_inner_from_dict = EvaluationV1alpha1SpecConfigEvaluationsInner.from_dict(evaluation_v1alpha1_spec_config_evaluations_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


