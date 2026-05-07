# EvaluationV1alpha1SpecConfigRulesInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** | Description explains what the rule validates | [optional] 
**expression** | **str** | Expression is a CEL expression that returns a boolean | 
**name** | **str** | Name identifies the rule | 
**weight** | **int** | Weight determines the rule&#39;s impact on the overall score (default: 1) | [optional] 

## Example

```python
from ark_sdk.models.evaluation_v1alpha1_spec_config_rules_inner import EvaluationV1alpha1SpecConfigRulesInner

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluationV1alpha1SpecConfigRulesInner from a JSON string
evaluation_v1alpha1_spec_config_rules_inner_instance = EvaluationV1alpha1SpecConfigRulesInner.from_json(json)
# print the JSON string representation of the object
print(EvaluationV1alpha1SpecConfigRulesInner.to_json())

# convert the object into a dict
evaluation_v1alpha1_spec_config_rules_inner_dict = evaluation_v1alpha1_spec_config_rules_inner_instance.to_dict()
# create an instance of EvaluationV1alpha1SpecConfigRulesInner from a dict
evaluation_v1alpha1_spec_config_rules_inner_from_dict = EvaluationV1alpha1SpecConfigRulesInner.from_dict(evaluation_v1alpha1_spec_config_rules_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


