# EvaluationV1alpha1SpecConfig

EvaluationConfig holds type-specific configuration parameters

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**concurrency** | **int** | Maximum number of concurrent child evaluations | [optional] [default to 10]
**continue_on_failure** | **bool** | Whether to continue on child evaluation failures | [optional] [default to False]
**evaluations** | [**List[EvaluationV1alpha1SpecConfigEvaluationsInner]**](EvaluationV1alpha1SpecConfigEvaluationsInner.md) | List of existing evaluations to aggregate (legacy support) | [optional] 
**input** | **str** |  | [optional] 
**items** | [**List[EvaluationV1alpha1SpecConfigItemsInner]**](EvaluationV1alpha1SpecConfigItemsInner.md) | List of specific evaluations to create (explicit definitions) | [optional] 
**output** | **str** |  | [optional] 
**query_ref** | [**EvaluationV1alpha1SpecConfigQueryRef**](EvaluationV1alpha1SpecConfigQueryRef.md) |  | [optional] 
**query_selector** | [**EvaluationV1alpha1SpecConfigQuerySelector**](EvaluationV1alpha1SpecConfigQuerySelector.md) |  | [optional] 
**rules** | [**List[EvaluationV1alpha1SpecConfigRulesInner]**](EvaluationV1alpha1SpecConfigRulesInner.md) |  | [optional] 
**template** | [**EvaluationV1alpha1SpecConfigTemplate**](EvaluationV1alpha1SpecConfigTemplate.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config import EvaluationV1alpha1SpecConfig

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfig from a JSON string
evaluation_v1alpha1_spec_config_instance = EvaluationV1alpha1SpecConfig.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfig.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_dict = evaluation_v1alpha1_spec_config_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfig from a dict
evaluation_v1alpha1_spec_config_from_dict = EvaluationV1alpha1SpecConfig.from_dict(evaluation_v1alpha1_spec_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


