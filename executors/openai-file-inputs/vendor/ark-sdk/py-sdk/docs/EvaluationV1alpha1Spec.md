# EvaluationV1alpha1Spec

EvaluationSpec defines the desired state of Evaluation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config** | [**EvaluationV1alpha1SpecConfig**](EvaluationV1alpha1SpecConfig.md) |  | 
**evaluator** | [**EvaluationV1alpha1SpecEvaluator**](EvaluationV1alpha1SpecEvaluator.md) |  | [optional] 
**timeout** | **str** | Timeout for query execution (e.g., \&quot;30s\&quot;, \&quot;5m\&quot;, \&quot;1h\&quot;) | [optional] [default to '5m']
**ttl** | **str** |  | [optional] [default to '720h']
**type** | **str** |  | [optional] [default to 'direct']

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec import EvaluationV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1Spec from a JSON string
evaluation_v1alpha1_spec_instance = EvaluationV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1Spec.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_dict = evaluation_v1alpha1_spec_instance.to_dict()
# create an instance of EvaluationV1alpha1Spec from a dict
evaluation_v1alpha1_spec_from_dict = EvaluationV1alpha1Spec.from_dict(evaluation_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


