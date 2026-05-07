# A2AServerV1prealpha1StatusConditionsInner

Condition contains details for one aspect of the current state of this API Resource.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**last_transition_time** | **str** | lastTransitionTime is the last time the condition transitioned from one status to another. This should be when the underlying condition changed.  If that is not known, then using the time when the API field changed is acceptable. | 
**message** | **str** | message is a human readable message indicating details about the transition. This may be an empty string. | 
**observed_generation** | **int** | observedGeneration represents the .metadata.generation that the condition was set based upon. For instance, if .metadata.generation is currently 12, but the .status.conditions[x].observedGeneration is 9, the condition is out of date with respect to the current state of the instance. | [optional] 
**reason** | **str** | reason contains a programmatic identifier indicating the reason for the condition&#39;s last transition. Producers of specific condition types may define expected values and meanings for this field, and whether the values are considered a guaranteed API. The value should be a CamelCase string. This field may not be empty. | 
**status** | **str** | status of the condition, one of True, False, Unknown. | 
**type** | **str** | type of condition in CamelCase or in foo.example.com/CamelCase. | 

## Example

```python
from ark_sdk.models.a2_a_server_v1prealpha1_status_conditions_inner import A2AServerV1prealpha1StatusConditionsInner

# TODO update the JSON string below
json = "{}"
# create an instance of A2AServerV1prealpha1StatusConditionsInner from a JSON string
a2_a_server_v1prealpha1_status_conditions_inner_instance = A2AServerV1prealpha1StatusConditionsInner.from_json(json)
# print the JSON string representation of the object
print(A2AServerV1prealpha1StatusConditionsInner.to_json())

# convert the object into a dict
a2_a_server_v1prealpha1_status_conditions_inner_dict = a2_a_server_v1prealpha1_status_conditions_inner_instance.to_dict()
# create an instance of A2AServerV1prealpha1StatusConditionsInner from a dict
a2_a_server_v1prealpha1_status_conditions_inner_from_dict = A2AServerV1prealpha1StatusConditionsInner.from_dict(a2_a_server_v1prealpha1_status_conditions_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


