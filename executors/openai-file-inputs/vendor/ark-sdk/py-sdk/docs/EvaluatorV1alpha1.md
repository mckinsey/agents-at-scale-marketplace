# EvaluatorV1alpha1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_version** | **str** | APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources | [optional] 
**kind** | **str** | Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds | [optional] 
**metadata** | **object** |  | [optional] 
**spec** | [**EvaluatorV1alpha1Spec**](EvaluatorV1alpha1Spec.md) |  | [optional] 
**status** | [**EvaluatorV1alpha1Status**](EvaluatorV1alpha1Status.md) |  | [optional] 

## Example

```python
from ark_sdk.models.evaluator_v1alpha1 import EvaluatorV1alpha1

# TODO update the JSON string below
json = "{}"
# create an instance of EvaluatorV1alpha1 from a JSON string
evaluator_v1alpha1_instance = EvaluatorV1alpha1.from_json(json)
# print the JSON string representation of the object
print(EvaluatorV1alpha1.to_json())

# convert the object into a dict
evaluator_v1alpha1_dict = evaluator_v1alpha1_instance.to_dict()
# create an instance of EvaluatorV1alpha1 from a dict
evaluator_v1alpha1_from_dict = EvaluatorV1alpha1.from_dict(evaluator_v1alpha1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


