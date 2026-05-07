# ToolV1alpha1SpecTeam

Team-specific configuration for team tools. This field is required only if Type = \"team\".

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the Team being referenced. This must be a non-empty string. | 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec_team import ToolV1alpha1SpecTeam

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1SpecTeam from a JSON string
tool_v1alpha1_spec_team_instance = ToolV1alpha1SpecTeam.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1SpecTeam.to_json())

# convert the object into a dict
tool_v1alpha1_spec_team_dict = tool_v1alpha1_spec_team_instance.to_dict()
# create an instance of ToolV1alpha1SpecTeam from a dict
tool_v1alpha1_spec_team_from_dict = ToolV1alpha1SpecTeam.from_dict(tool_v1alpha1_spec_team_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


