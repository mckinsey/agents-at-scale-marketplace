# TeamV1alpha1Status


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conditions** | [**List[A2AServerV1prealpha1StatusConditionsInner]**](A2AServerV1prealpha1StatusConditionsInner.md) |  | [optional] 

## Example

```python
from ark_sdk.models.team_v1alpha1_status import TeamV1alpha1Status

# TODO update the JSON string below
json = "{}"
# create an instance of TeamV1alpha1Status from a JSON string
team_v1alpha1_status_instance = TeamV1alpha1Status.from_json(json)
# print the JSON string representation of the object
print(TeamV1alpha1Status.to_json())

# convert the object into a dict
team_v1alpha1_status_dict = team_v1alpha1_status_instance.to_dict()
# create an instance of TeamV1alpha1Status from a dict
team_v1alpha1_status_from_dict = TeamV1alpha1Status.from_dict(team_v1alpha1_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


