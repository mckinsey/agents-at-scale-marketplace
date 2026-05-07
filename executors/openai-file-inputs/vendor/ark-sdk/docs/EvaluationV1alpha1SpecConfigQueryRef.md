# EvaluationV1alpha1SpecConfigQueryRef

QueryRef references a query for post-hoc evaluation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**namespace** | **str** |  | [optional] 
**response_target** | **str** | Target name to match against query responses (e.g., \&quot;weather-agent\&quot;, \&quot;summary-team\&quot;) | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_query_ref import EvaluationV1alpha1SpecConfigQueryRef

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigQueryRef from a JSON string
evaluation_v1alpha1_spec_config_query_ref_instance = EvaluationV1alpha1SpecConfigQueryRef.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigQueryRef.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_query_ref_dict = evaluation_v1alpha1_spec_config_query_ref_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigQueryRef from a dict
evaluation_v1alpha1_spec_config_query_ref_from_dict = EvaluationV1alpha1SpecConfigQueryRef.from_dict(evaluation_v1alpha1_spec_config_query_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


