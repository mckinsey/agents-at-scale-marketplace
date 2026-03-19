import logging
from typing import Optional
from dataclasses import dataclass

from .model_resolver import _get_k8s_client, K8S_AVAILABLE

logger = logging.getLogger(__name__)

if K8S_AVAILABLE:
    from kubernetes import client


@dataclass
class AgentInstructions:
    name: str
    description: str
    system_prompt: str


class AgentResolver:
    def __init__(self):
        self.k8s_client = _get_k8s_client()
        if not self.k8s_client:
            logger.warning("Kubernetes client not available - agent context resolution will be limited")

    async def resolve_agent_instructions(self, agent_name: str, namespace: str = "default") -> Optional[AgentInstructions]:
        if not self.k8s_client or not K8S_AVAILABLE:
            logger.warning(f"Cannot resolve agent {agent_name}: Kubernetes client not available")
            return None

        try:
            custom_api = client.CustomObjectsApi(self.k8s_client)
            agent_resource = custom_api.get_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=namespace,
                plural="agents",
                name=agent_name
            )

            metadata = agent_resource.get("metadata", {})
            spec = agent_resource.get("spec", {})

            return AgentInstructions(
                name=metadata.get("name", agent_name),
                description=spec.get("description", ""),
                system_prompt=spec.get("prompt", ""),
            )

        except Exception as e:
            logger.error(f"Error resolving agent {agent_name}: {e}")
            return None
