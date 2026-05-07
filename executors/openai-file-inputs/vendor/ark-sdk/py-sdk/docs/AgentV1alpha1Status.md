# AgentV1alpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) | Conditions represent the latest available observations of an agent&#39;s state | [optional] 

## Example

```python
from ark_sdk.models.agent_v1alpha1_status import AgentV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of AgentV1alpha1Status from a JSON string
agent_v1alpha1_status_instance = AgentV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(AgentV1alpha1Status.to_json())

# convert the object into a dict
agent_v1alpha1_status_dict = agent_v1alpha1_status_instance.to_dict()
# create an instance of AgentV1alpha1Status from a dict
agent_v1alpha1_status_from_dict = AgentV1alpha1Status.from_dict(agent_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


