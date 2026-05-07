# TeamV1alpha1SpecSelector


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent** | **str** |  | [optional] 
**enable_terminate_tool** | **bool** |  | [optional] 
**selector_prompt** | **str** |  | [optional] 
**terminate_prompt** | **str** |  | [optional] 

## Example

```python
from ark_sdk.models.team_v1alpha1_spec_selector import TeamV1alpha1SpecSelector

# TODO update the JSON string below
json = "{}"
# create an instance of TeamV1alpha1SpecSelector from a JSON string
team_v1alpha1_spec_selector_instance = TeamV1alpha1SpecSelector.from_json(json)
# print the JSON string representation of the object
print(TeamV1alpha1SpecSelector.to_json())

# convert the object into a dict
team_v1alpha1_spec_selector_dict = team_v1alpha1_spec_selector_instance.to_dict()
# create an instance of TeamV1alpha1SpecSelector from a dict
team_v1alpha1_spec_selector_from_dict = TeamV1alpha1SpecSelector.from_dict(team_v1alpha1_spec_selector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


