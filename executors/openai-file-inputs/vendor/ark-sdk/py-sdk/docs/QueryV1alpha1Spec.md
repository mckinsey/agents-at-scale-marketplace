# QueryV1alpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**cancel** | **bool** | When true, indicates intent to cancel the query | [optional] 
**conversation_id** | **str** | ConversationId is sent as A2A ContextID when dispatching to execution engines. Engines use it for conversation threading (e.g., memory lookup, session management). | [optional] 
**input** | **object** |  | 
**memory** | [**AgentV1alpha1SpecModelRef**](AgentV1alpha1SpecModelRef.md) |  | [optional] 
**overrides** | [**List[AgentV1alpha1SpecOverridesInner]**](AgentV1alpha1SpecOverridesInner.md) |  | [optional] 
**parameters** | [**List[AgentV1alpha1SpecParametersInner]**](AgentV1alpha1SpecParametersInner.md) | Parameters for template processing in the input field | [optional] 
**selector** | [**AgentV1alpha1SpecOverridesInnerLabelSelector**](AgentV1alpha1SpecOverridesInnerLabelSelector.md) |  | [optional] 
**service_account** | **str** |  | [optional] 
**session_id** | **str** |  | [optional] 
**target** | [**QueryV1alpha1SpecTarget**](QueryV1alpha1SpecTarget.md) |  | [optional] 
**timeout** | **str** | Timeout for query execution (e.g., \&quot;30s\&quot;, \&quot;5m\&quot;, \&quot;1h\&quot;) | [optional] [default to '5m']
**ttl** | **str** |  | [optional] [default to '720h']
**type** | **str** |  | [optional] [default to 'user']

## Example

```python
from ark_sdk.models.query_v1alpha1_spec import QueryV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of QueryV1alpha1Spec from a JSON string
query_v1alpha1_spec_instance = QueryV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(QueryV1alpha1Spec.to_json())

# convert the object into a dict
query_v1alpha1_spec_dict = query_v1alpha1_spec_instance.to_dict()
# create an instance of QueryV1alpha1Spec from a dict
query_v1alpha1_spec_from_dict = QueryV1alpha1Spec.from_dict(query_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


