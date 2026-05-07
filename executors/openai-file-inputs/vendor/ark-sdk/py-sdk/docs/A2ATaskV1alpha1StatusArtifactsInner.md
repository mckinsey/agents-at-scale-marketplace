# A2ATaskV1alpha1StatusArtifactsInner

A2ATaskArtifact represents artifacts produced during A2A task execution. Artifacts contain structured content with one or more parts.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**artifact_id** | **str** | ArtifactID uniquely identifies this artifact within the task. | 
**description** | **str** | Description provides additional context about the artifact. | [optional] 
**metadata** | **object** | Metadata contains additional key-value pairs for this artifact. | [optional] 
**name** | **str** | Name is a human-readable name for the artifact. | [optional] 
**parts** | [**List[A2ATaskV1alpha1StatusArtifactsInnerPartsInner]**](A2ATaskV1alpha1StatusArtifactsInnerPartsInner.md) | Parts contains the content of the artifact as one or more parts. | 

## Example

```python
from ark_sdk.models.a2_a_task_v1alpha1_status_artifacts_inner import A2ATaskV1alpha1StatusArtifactsInner

# TODO update the JSON string below
json = "{}"
# create an instance of A2ATaskV1alpha1StatusArtifactsInner from a JSON string
a2_a_task_v1alpha1_status_artifacts_inner_instance = A2ATaskV1alpha1StatusArtifactsInner.from_json(json)
# print the JSON string representation of the object
print(A2ATaskV1alpha1StatusArtifactsInner.to_json())

# convert the object into a dict
a2_a_task_v1alpha1_status_artifacts_inner_dict = a2_a_task_v1alpha1_status_artifacts_inner_instance.to_dict()
# create an instance of A2ATaskV1alpha1StatusArtifactsInner from a dict
a2_a_task_v1alpha1_status_artifacts_inner_from_dict = A2ATaskV1alpha1StatusArtifactsInner.from_dict(a2_a_task_v1alpha1_status_artifacts_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


