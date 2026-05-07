# TeamV1alpha1Spec


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** |  | [optional] 
**graph** | [**TeamV1alpha1SpecGraph**](TeamV1alpha1SpecGraph.md) |  | [optional] 
**loops** | **bool** |  | [default to False]
**max_turns** | **int** |  | [optional] 
**members** | [**List[TeamV1alpha1SpecMembersInner]**](TeamV1alpha1SpecMembersInner.md) |  | 
**selector** | [**TeamV1alpha1SpecSelector**](TeamV1alpha1SpecSelector.md) |  | [optional] 
**strategy** | **str** |  | 

## Example

```python
from ark_sdk.models.team_v1alpha1_spec import TeamV1alpha1Spec

# TODO update the JSON string below
json = "{}"
# create an instance of TeamV1alpha1Spec from a JSON string
team_v1alpha1_spec_instance = TeamV1alpha1Spec.from_json(json)
# print the JSON string representation of the object
print(TeamV1alpha1Spec.to_json())

# convert the object into a dict
team_v1alpha1_spec_dict = team_v1alpha1_spec_instance.to_dict()
# create an instance of TeamV1alpha1Spec from a dict
team_v1alpha1_spec_from_dict = TeamV1alpha1Spec.from_dict(team_v1alpha1_spec_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


