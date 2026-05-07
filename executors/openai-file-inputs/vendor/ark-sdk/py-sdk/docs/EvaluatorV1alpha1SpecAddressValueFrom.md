# EvaluatorV1alpha1SpecAddressValueFrom


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**config_map_key_ref** | [**A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef**](A2AServerV1prealpha1SpecAddressValueFromConfigMapKeyRef.md) |  | [optional] 
**query_parameter_ref** | [**AgentV1alpha1SpecParametersInnerValueFromQueryParameterRef**](AgentV1alpha1SpecParametersInnerValueFromQueryParameterRef.md) |  | [optional] 
**secret_key_ref** | [**A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef**](A2AServerV1prealpha1SpecAddressValueFromSecretKeyRef.md) |  | [optional] 
**service_ref** | [**A2AServerV1prealpha1SpecAddressValueFromServiceRef**](A2AServerV1prealpha1SpecAddressValueFromServiceRef.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1_spec_address_value_from import EvaluatorV1alpha1SpecAddressValueFrom

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1SpecAddressValueFrom from a JSON string
evaluator_v1alpha1_spec_address_value_from_instance = EvaluatorV1alpha1SpecAddressValueFrom.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1SpecAddressValueFrom.to_json())

# convert the object into a dict
evaluator_v1alpha1_spec_address_value_from_dict = evaluator_v1alpha1_spec_address_value_from_instance.to_dict()
# create an instance of EvaluatorV1alpha1SpecAddressValueFrom from a dict
evaluator_v1alpha1_spec_address_value_from_from_dict = EvaluatorV1alpha1SpecAddressValueFrom.from_dict(evaluator_v1alpha1_spec_address_value_from_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


