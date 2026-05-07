# ToolV1alpha1SpecHttp

HTTP-specific configuration for HTTP-based tools

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**body** | **str** | Body template for POST/PUT/PATCH requests with golang template syntax | [optional] 
**body_parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) | Parameters for body template processing | [optional] 
**headers** | [**List[A2AServerV1prealpha1SpecHeadersInner]**](A2AServerV1prealpha1SpecHeadersInner.md) |  | [optional] 
**method** | **str** |  | [optional] [default to 'GET']
**timeout** | **str** |  | [optional] 
**url** | **str** |  | 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec_http import ToolV1alpha1SpecHttp

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1SpecHttp from a JSON string
tool_v1alpha1_spec_http_instance = ToolV1alpha1SpecHttp.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1SpecHttp.to_json())

# convert the object into a dict
tool_v1alpha1_spec_http_dict = tool_v1alpha1_spec_http_instance.to_dict()
# create an instance of ToolV1alpha1SpecHttp from a dict
tool_v1alpha1_spec_http_from_dict = ToolV1alpha1SpecHttp.from_dict(tool_v1alpha1_spec_http_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


