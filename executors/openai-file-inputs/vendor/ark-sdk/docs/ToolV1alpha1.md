# ToolV1alpha1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_version** | **str** | APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources | [optional] 
**kind** | **str** | Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds | [optional] 
**metadata** | **object** |  | [optional] 
**spec** | [**ToolV1alpha1Spec**](ToolV1alpha1Spec.md) |  | [optional] 
**status** | [**ToolV1alpha1Status**](ToolV1alpha1Status.md) |  | [optional] 

## Example

```python
from ark_sdk.models.tool_v1alpha1 import ToolV1alpha1

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1 from a JSON string
tool_v1alpha1_instance = ToolV1alpha1.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1.to_json())

# convert the object into a dict
tool_v1alpha1_dict = tool_v1alpha1_instance.to_dict()
# create an instance of ToolV1alpha1 from a dict
tool_v1alpha1_from_dict = ToolV1alpha1.from_dict(tool_v1alpha1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


