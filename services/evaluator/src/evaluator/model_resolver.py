import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

_k8s_client_cache = None
_k8s_client_initialized = False

KUBERNETES_INTEGRATION = os.getenv("KUBERNETES_INTEGRATION", "true").lower() == "true"


class ModelConfig:
    def __init__(self, model: str, base_url: str, api_key: str, api_version: str = "2024-02-15"):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version


def _get_k8s_client():
    global _k8s_client_cache, _k8s_client_initialized

    if not K8S_AVAILABLE or not KUBERNETES_INTEGRATION:
        _k8s_client_initialized = True
        return None

    if not _k8s_client_initialized:
        try:
            config.load_incluster_config()
            _k8s_client_cache = client.ApiClient()
            logger.info("Loaded in-cluster Kubernetes configuration (cached)")
        except Exception:
            try:
                config.load_kube_config()
                _k8s_client_cache = client.ApiClient()
                logger.info("Loaded kubeconfig configuration (cached)")
            except Exception as e:
                logger.warning(f"No Kubernetes configuration available: {e}")
                _k8s_client_cache = None

        _k8s_client_initialized = True

    return _k8s_client_cache


class ModelResolver:
    def __init__(self):
        self.k8s_client = _get_k8s_client()

    async def resolve_model(self, model_ref=None, query_context: Optional[Dict[str, Any]] = None) -> ModelConfig:
        logger.info(f"Starting model resolution - model_ref: {model_ref}, k8s_available: {self.k8s_client is not None}")

        if self.k8s_client is None:
            logger.info("No Kubernetes client available, using environment-based model config")
            return self._get_system_default_model()

        try:
            if model_ref:
                logger.info(f"Resolving from explicit model reference: {model_ref.name}")
                return self._resolve_from_model_ref(model_ref)

            if query_context and 'spec' in query_context:
                query_spec = query_context['spec']
                if 'modelRef' in query_spec:
                    model_ref_data = query_spec['modelRef']
                    logger.info(f"Resolving from query context modelRef: {model_ref_data}")
                    return self._resolve_from_query_model_ref(model_ref_data, query_context)

            logger.info("No explicit model reference found, resolving default model")
            return self._resolve_default_model(query_context)

        except Exception as e:
            logger.error(f"Failed to resolve model: {e}")
            return self._get_system_default_model()

    def _resolve_from_model_ref(self, model_ref) -> ModelConfig:
        namespace = model_ref.namespace or "default"
        model_crd = self._load_model_crd(model_ref.name, namespace)
        return self._extract_model_config_from_crd(model_crd)

    def _resolve_from_query_model_ref(self, model_ref_data: Dict[str, Any],
                                    query_context: Dict[str, Any]) -> ModelConfig:
        model_name = model_ref_data.get('name', 'default')
        namespace = model_ref_data.get('namespace', query_context.get('metadata', {}).get('namespace', 'default'))
        model_crd = self._load_model_crd(model_name, namespace)
        return self._extract_model_config_from_crd(model_crd)

    def _resolve_default_model(self, query_context: Optional[Dict[str, Any]] = None) -> ModelConfig:
        namespace = "default"
        if query_context and 'metadata' in query_context:
            namespace = query_context['metadata'].get('namespace', 'default')

        try:
            model_crd = self._load_model_crd('default', namespace)
            return self._extract_model_config_from_crd(model_crd)
        except Exception as e:
            logger.warning(f"Could not load default model in namespace {namespace}: {e}")
            return self._get_system_default_model()

    def _load_model_crd(self, name: str, namespace: str) -> Dict[str, Any]:
        custom_api = client.CustomObjectsApi(self.k8s_client)
        try:
            return custom_api.get_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=namespace,
                plural="models",
                name=name
            )
        except client.rest.ApiException as e:
            if e.status == 404:
                raise ValueError(f"Model '{name}' not found in namespace '{namespace}'")
            elif e.status == 403:
                raise ValueError(f"Access denied to model '{name}' in namespace '{namespace}'")
            else:
                raise ValueError(f"Error loading model '{name}': {e}")

    def _extract_model_config_from_crd(self, model_crd: Dict[str, Any]) -> ModelConfig:
        spec = model_crd.get('spec', {})
        model_name = spec.get('model', {}).get('value', 'gpt-4')
        model_type = spec.get('type', 'openai')
        provider = spec.get('provider', model_type)
        config_data = spec.get('config', {})

        if provider == 'azure' or model_type == 'azure':
            azure_config = config_data.get('azure', {})
            base_url = azure_config.get('baseUrl', {}).get('value', '')
            api_key = self._resolve_value_source(azure_config.get('apiKey', {}), model_crd.get('metadata', {}).get('namespace', 'default'))
            api_version = azure_config.get('apiVersion', {}).get('value', '2024-02-15')
        elif provider == 'openai' or model_type == 'openai':
            openai_config = config_data.get('openai', {})
            base_url = openai_config.get('baseUrl', {}).get('value', 'https://api.openai.com/v1')
            api_key = self._resolve_value_source(openai_config.get('apiKey', {}), model_crd.get('metadata', {}).get('namespace', 'default'))
            api_version = openai_config.get('apiVersion', {}).get('value', '2024-02-15')
        else:
            base_url = "https://api.openai.com/v1"
            api_key = "demo-key"
            api_version = "2024-02-15"

        return ModelConfig(model=model_name, base_url=base_url, api_key=api_key, api_version=api_version)

    def _resolve_value_source(self, value_source: Dict[str, Any], namespace: str) -> str:
        if 'value' in value_source:
            return value_source['value']
        elif 'valueFrom' in value_source:
            value_from = value_source['valueFrom']
            if 'secretKeyRef' in value_from:
                return self._resolve_secret_key_ref(value_from['secretKeyRef'], namespace)
            elif 'configMapKeyRef' in value_from:
                return self._resolve_configmap_key_ref(value_from['configMapKeyRef'], namespace)
        return "demo-key"

    def _resolve_secret_key_ref(self, secret_key_ref: Dict[str, Any], namespace: str) -> str:
        secret_name = secret_key_ref.get('name')
        secret_key = secret_key_ref.get('key')
        if not secret_name or not secret_key:
            return "invalid-secret-ref"
        if self.k8s_client is None:
            return "no-k8s-client"
        try:
            import base64
            v1 = client.CoreV1Api(self.k8s_client)
            secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
            if secret.data and secret_key in secret.data:
                return base64.b64decode(secret.data[secret_key]).decode('utf-8')
            return "missing-secret-key"
        except Exception as e:
            logger.error(f"Error resolving secret '{secret_name}.{secret_key}': {e}")
            return "secret-error"

    def _resolve_configmap_key_ref(self, configmap_key_ref: Dict[str, Any], namespace: str) -> str:
        configmap_name = configmap_key_ref.get('name')
        configmap_key = configmap_key_ref.get('key')
        if not configmap_name or not configmap_key:
            return "invalid-configmap-ref"
        if self.k8s_client is None:
            return "no-k8s-client"
        try:
            v1 = client.CoreV1Api(self.k8s_client)
            configmap = v1.read_namespaced_config_map(name=configmap_name, namespace=namespace)
            if configmap.data and configmap_key in configmap.data:
                return configmap.data[configmap_key]
            return "missing-configmap-key"
        except Exception as e:
            logger.error(f"Error resolving configmap '{configmap_name}.{configmap_key}': {e}")
            return "configmap-error"

    def _get_system_default_model(self) -> ModelConfig:
        return ModelConfig(
            model=os.getenv("DEFAULT_MODEL_NAME", "gpt-4o-mini"),
            base_url=os.getenv("DEFAULT_MODEL_ENDPOINT", "https://api.openai.com/v1"),
            api_key=os.getenv("DEFAULT_MODEL_API_KEY", "demo-key"),
            api_version=os.getenv("DEFAULT_MODEL_API_VERSION", "2024-02-15")
        )
