import logging
from typing import Optional, Dict, Any
from ..types import QueryRef

logger = logging.getLogger(__name__)

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False


class QueryResolver:

    def __init__(self):
        self.k8s_client = None
        if K8S_AVAILABLE:
            try:
                config.load_incluster_config()
                self.k8s_client = client.ApiClient()
            except Exception:
                try:
                    config.load_kube_config()
                    self.k8s_client = client.ApiClient()
                except Exception as e:
                    logger.warning(f"Could not load Kubernetes configuration: {e}")

    async def resolve_query(self, query_ref: QueryRef):
        if not self.k8s_client:
            raise RuntimeError("Kubernetes client not available for query resolution")

        try:
            query_crd = self._load_query_crd(query_ref.name, query_ref.namespace or "default")
            return query_crd
        except Exception as e:
            logger.error(f"Failed to resolve query {query_ref.name}: {e}")
            raise

    def _load_query_crd(self, name: str, namespace: str) -> Dict[str, Any]:
        custom_api = client.CustomObjectsApi(self.k8s_client)
        try:
            return custom_api.get_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=namespace,
                plural="queries",
                name=name
            )
        except client.rest.ApiException as e:
            if e.status == 404:
                raise ValueError(f"Query '{name}' not found in namespace '{namespace}'")
            elif e.status == 403:
                raise ValueError(f"Access denied to query '{name}' in namespace '{namespace}'")
            else:
                raise ValueError(f"Error loading query '{name}': {e}")

    def extract_metrics_from_query(self, query) -> Dict[str, Any]:
        try:
            metrics = {}

            if isinstance(query, dict):
                status = query.get('status')
                query_name = query.get('metadata', {}).get('name', 'unknown')
            else:
                status = getattr(query, 'status', None)
                query_name = getattr(getattr(query, 'metadata', None), 'name', 'unknown') if hasattr(query, 'metadata') else 'unknown'

            if not status:
                return self._extract_basic_metadata(query, metrics)

            self._extract_token_metrics(status, metrics)
            self._extract_timing_metrics(status, metrics)
            self._extract_response_metrics(status, metrics)
            self._extract_status_metrics(status, metrics)
            self._extract_basic_metadata(query, metrics)
            self._extract_model_name(query, metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to extract metrics from query: {e}")
            return {}

    def _extract_token_metrics(self, status, metrics: Dict[str, Any]) -> None:
        token_usage = None
        if isinstance(status, dict):
            token_usage = status.get('tokenUsage') or status.get('token_usage')
        else:
            token_usage = getattr(status, 'token_usage', None) or getattr(status, 'tokenUsage', None)

        if token_usage:
            if isinstance(token_usage, dict):
                metrics.update({
                    "totalTokens": token_usage.get('totalTokens', 0),
                    "promptTokens": token_usage.get('promptTokens', 0),
                    "completionTokens": token_usage.get('completionTokens', 0),
                })
            else:
                metrics.update({
                    "totalTokens": getattr(token_usage, 'total_tokens', 0),
                    "promptTokens": getattr(token_usage, 'prompt_tokens', 0),
                    "completionTokens": getattr(token_usage, 'completion_tokens', 0),
                })

            prompt_tokens = metrics.get("promptTokens", 0)
            completion_tokens = metrics.get("completionTokens", 0)
            if prompt_tokens > 0:
                metrics["tokenEfficiency"] = completion_tokens / prompt_tokens
            else:
                metrics["tokenEfficiency"] = 0

    def _extract_timing_metrics(self, status, metrics: Dict[str, Any]) -> None:
        import time
        from datetime import datetime

        duration_seconds = None

        duration_field = status.get('duration') if isinstance(status, dict) else getattr(status, 'duration', None)

        if duration_field:
            try:
                if isinstance(duration_field, str):
                    duration_seconds = self._parse_duration_string(duration_field)
                elif isinstance(duration_field, (int, float)):
                    duration_seconds = float(duration_field)
            except Exception as e:
                logger.warning(f"Failed to parse duration field: {e}")

        if duration_seconds is not None and duration_seconds > 0:
            metrics["executionDuration"] = f"{duration_seconds:.2f}s"
            metrics["executionDurationSeconds"] = duration_seconds

            total_tokens = metrics.get("totalTokens", 0)
            if total_tokens > 0:
                metrics["tokensPerSecond"] = total_tokens / duration_seconds

        metrics["evaluationTimestamp"] = time.time()

    def _extract_response_metrics(self, status, metrics: Dict[str, Any]) -> None:
        response = None
        if isinstance(status, dict):
            response = status.get('response')
        else:
            response = getattr(status, 'response', None)

        if response:
            content_length = 0
            if isinstance(response, dict):
                content = response.get('content', '')
                if content:
                    content_length = len(content)
            else:
                if hasattr(response, 'content') and response.content:
                    content_length = len(response.content)

            metrics.update({
                "responseCount": 1,
                "totalResponseLength": content_length,
                "averageResponseLength": content_length,
            })

            if content_length > 0:
                metrics["responseCompleteness"] = min(1.0, content_length / 50)

    def _extract_status_metrics(self, status, metrics: Dict[str, Any]) -> None:
        phase = status.get('phase') if isinstance(status, dict) else getattr(status, 'phase', None)
        if phase:
            metrics["queryPhase"] = phase
            metrics["isCompleted"] = phase in ["done", "completed", "success"]
            metrics["hasErrors"] = phase in ["error", "failed"]

    def _extract_basic_metadata(self, query, metrics: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(query, dict):
            metadata = query.get('metadata')
            if metadata:
                metrics["queryName"] = metadata.get('name', 'unknown')
                metrics["queryNamespace"] = metadata.get('namespace', 'default')
                labels = metadata.get('labels')
                if labels:
                    metrics["labels"] = dict(labels)
                    if "model" in metrics["labels"]:
                        metrics["modelName"] = metrics["labels"]["model"]
        return metrics

    def _parse_duration_string(self, duration_str: str) -> float:
        import re

        duration_str = duration_str.strip().lower()

        simple_match = re.match(r'^(\d+\.?\d*)s?$', duration_str)
        if simple_match:
            return float(simple_match.group(1))

        total_seconds = 0.0
        hours_match = re.search(r'(\d+\.?\d*)h', duration_str)
        minutes_match = re.search(r'(\d+\.?\d*)m', duration_str)
        seconds_match = re.search(r'(\d+\.?\d*)s', duration_str)

        if hours_match:
            total_seconds += float(hours_match.group(1)) * 3600
        if minutes_match:
            total_seconds += float(minutes_match.group(1)) * 60
        if seconds_match:
            total_seconds += float(seconds_match.group(1))

        if total_seconds == 0:
            total_seconds = float(duration_str)

        return total_seconds

    def _extract_model_name(self, query, metrics: Dict[str, Any]) -> None:
        try:
            targets = None
            if isinstance(query, dict):
                targets = query.get('spec', {}).get('targets', [])

            if not targets or not self.k8s_client:
                return

            for target in targets:
                target_type = target.get('type') if isinstance(target, dict) else getattr(target, 'type', None)
                target_name = target.get('name') if isinstance(target, dict) else getattr(target, 'name', None)

                if target_type == 'agent' and target_name:
                    agent_model = self._get_agent_model_name(target_name, metrics.get("queryNamespace", "default"))
                    if agent_model:
                        metrics["modelName"] = agent_model
                        return
        except Exception as e:
            logger.error(f"Failed to extract model name: {e}")

    def _get_agent_model_name(self, agent_name: str, namespace: str) -> Optional[str]:
        if not self.k8s_client:
            return None
        try:
            custom_api = client.CustomObjectsApi(self.k8s_client)
            agent = custom_api.get_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=namespace,
                plural="agents",
                name=agent_name
            )
            return agent.get('spec', {}).get('modelRef', {}).get('name')
        except Exception as e:
            logger.warning(f"Failed to lookup agent '{agent_name}': {e}")
            return None
