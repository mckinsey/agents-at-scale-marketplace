# A2ATaskV1alpha1StatusArtifactsInnerPartsInner

A2ATaskPart represents content parts compatible with A2A protocol. Parts can contain text, binary data, or file references.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | **str** | Data contains base64-encoded binary content when Kind is \&quot;data\&quot;. | [optional] 
**kind** | **str** | Kind specifies the type of content: \&quot;text\&quot;, \&quot;file\&quot;, or \&quot;data\&quot;. | 
**metadata** | **object** | Metadata contains additional key-value pairs for this part. | [optional] 
**mime_type** | **str** | MimeType specifies the content type (e.g., \&quot;text/plain\&quot;, \&quot;application/json\&quot;). | [optional] 
**text** | **str** | Text contains the actual text content when Kind is \&quot;text\&quot;. | [optional] 
**uri** | **str** | URI references an external resource when Kind is \&quot;file\&quot;. | [optional] 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_status_artifacts_inner_parts_inner import A2ATaskV1alpha1StatusArtifactsInnerPartsInner

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1StatusArtifactsInnerPartsInner from a JSON string
a2_a_task_v1alpha1_status_artifacts_inner_parts_inner_instance = A2ATaskV1alpha1StatusArtifactsInnerPartsInner.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1StatusArtifactsInnerPartsInner.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_status_artifacts_inner_parts_inner_dict = a2_a_task_v1alpha1_status_artifacts_inner_parts_inner_instance.to_dict()
# create an instance of A2ATaskV1alpha1StatusArtifactsInnerPartsInner from a dict
a2_a_task_v1alpha1_status_artifacts_inner_parts_inner_from_dict = A2ATaskV1alpha1StatusArtifactsInnerPartsInner.from_dict(a2_a_task_v1alpha1_status_artifacts_inner_parts_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


