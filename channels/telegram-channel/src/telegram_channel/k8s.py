import asyncio
import functools
import logging
import time
import uuid

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger("telegram-channel")

GROUP = "ark.mckinsey.com"
VERSION = "v1alpha1"


class K8sClient:
    def __init__(self, namespace: str = "default"):
        try:
            config.load_incluster_config()
            logger.info("Using in-cluster Kubernetes config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Using kubeconfig")
        self.api = client.CustomObjectsApi()
        self.core = client.CoreV1Api()
        self.namespace = namespace

    def get_secret(self, name: str) -> dict | None:
        try:
            s = self.core.read_namespaced_secret(name, self.namespace)
            import base64
            return {
                k: base64.b64decode(v).decode() for k, v in (s.data or {}).items()
            }
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def save_secret(self, name: str, data: dict):
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name),
            string_data=data,
        )
        try:
            self.core.read_namespaced_secret(name, self.namespace)
            self.core.replace_namespaced_secret(name, self.namespace, secret)
            logger.info(f"Updated secret {name}")
        except ApiException as e:
            if e.status == 404:
                self.core.create_namespaced_secret(self.namespace, secret)
                logger.info(f"Created secret {name}")
            else:
                raise

    def list_agents(self) -> list[dict]:
        result = self.api.list_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=self.namespace,
            plural="agents",
        )
        agents = []
        for a in result.get("items", []):
            name = a["metadata"]["name"]
            desc = a.get("spec", {}).get("description", "")
            agents.append({"name": name, "description": desc})
        return agents

    def create_query(
        self,
        agent: str,
        prompt: str,
        conversation_id: str,
        session_id: str,
    ) -> dict:
        name = f"tg-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        body = {
            "apiVersion": f"{GROUP}/{VERSION}",
            "kind": "Query",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": {
                    "ark.mckinsey.com/channel": "telegram",
                },
            },
            "spec": {
                "type": "user",
                "input": prompt,
                "target": {
                    "type": "agent",
                    "name": agent,
                },
                "conversationId": conversation_id,
                "sessionId": session_id,
                "ttl": "1h",
            },
        }
        logger.info(f"Creating query {name} for agent={agent}")
        return self.api.create_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=self.namespace,
            plural="queries",
            body=body,
        )

    def wait_for_query(self, name: str, timeout: int = 120) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            obj = self.api.get_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=self.namespace,
                plural="queries",
                name=name,
            )
            phase = obj.get("status", {}).get("phase", "")
            if phase == "done":
                content = obj["status"].get("response", {}).get("content", "")
                logger.info(f"Query {name} completed ({len(content)} chars)")
                return content or "(empty response)"
            elif phase == "error":
                response = obj.get("status", {}).get("response", {})
                error = response.get("content", "") or "Unknown error"
                logger.warning(f"Query {name} failed: {error}")
                raise RuntimeError(error)
            time.sleep(1)
        raise TimeoutError(f"Query {name} timed out after {timeout}s")

    async def submit_query(
        self,
        agent: str,
        prompt: str,
        conversation_id: str,
        session_id: str,
    ) -> str:
        loop = asyncio.get_event_loop()
        query = await loop.run_in_executor(
            None,
            functools.partial(
                self.create_query, agent, prompt, conversation_id, session_id
            ),
        )
        name = query["metadata"]["name"]
        return await loop.run_in_executor(
            None, functools.partial(self.wait_for_query, name)
        )
