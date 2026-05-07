# ToolV1alpha1SpecAnnotations

Optional additional tool information

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**destructive_hint** | **bool** | If true, the tool may perform destructive updates to its environment. If false, the tool performs only additive updates.  (This property is meaningful only when &#x60;readOnlyHint &#x3D;&#x3D; false&#x60;)  Default: true | [optional] 
**idempotent_hint** | **bool** | If true, calling the tool repeatedly with the same arguments will have no additional effect on the its environment.  (This property is meaningful only when &#x60;readOnlyHint &#x3D;&#x3D; false&#x60;)  Default: false | [optional] 
**open_world_hint** | **bool** | If true, this tool may interact with an \&quot;open world\&quot; of external entities. If false, the tool&#39;s domain of interaction is closed.  Default: true | [optional] 
**read_only_hint** | **bool** | If true, the tool does not modify its environment.  Default: false | [optional] 
**title** | **str** | A human-readable title for the tool. | [optional] 

## Example

```python
from ark_sdk.models.tool_v1alpha1_spec_annotations import ToolV1alpha1SpecAnnotations

# TODO update the JSON string below
json = "{}"
# create an instance of ToolV1alpha1SpecAnnotations from a JSON string
tool_v1alpha1_spec_annotations_instance = ToolV1alpha1SpecAnnotations.from_json(json)
# print the JSON string representation of the object
print(ToolV1alpha1SpecAnnotations.to_json())

# convert the object into a dict
tool_v1alpha1_spec_annotations_dict = tool_v1alpha1_spec_annotations_instance.to_dict()
# create an instance of ToolV1alpha1SpecAnnotations from a dict
tool_v1alpha1_spec_annotations_from_dict = ToolV1alpha1SpecAnnotations.from_dict(tool_v1alpha1_spec_annotations_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


