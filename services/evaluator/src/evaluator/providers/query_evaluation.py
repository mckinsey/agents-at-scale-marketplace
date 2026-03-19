from fastapi import HTTPException
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .base import EvaluationProvider
from ..types import (
    UnifiedEvaluationRequest, EvaluationResponse, EvaluationRequest,
    Response, QueryTarget, EvaluationParameters
)
from ..evaluator import LLMEvaluator

logger = logging.getLogger(__name__)


class QueryEvaluationProvider(EvaluationProvider):

    def get_evaluation_type(self) -> str:
        return "query"

    async def evaluate(self, request: UnifiedEvaluationRequest) -> EvaluationResponse:
        logger.info(f"Processing query evaluation with evaluator: {request.evaluatorName}")

        if not request.config or not hasattr(request.config, 'queryRef'):
            raise HTTPException(status_code=422, detail="Query evaluation requires queryRef in config")

        query_ref = request.config.queryRef
        query_name = query_ref.name
        query_namespace = query_ref.namespace or "default"
        response_target = query_ref.responseTarget

        try:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

            api_client = client.ApiClient()
            custom_api = client.CustomObjectsApi(api_client)

            query_resource = custom_api.get_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=query_namespace,
                plural="queries",
                name=query_name
            )

            input_text = query_resource["spec"].get("input", "")

            actual_agent_name = None
            target = query_resource.get("spec", {}).get("target")
            if target and target.get("type") == "agent":
                actual_agent_name = target.get("name")

            output_text = ""
            response = query_resource.get("status", {}).get("response")
            if response:
                output_text = response.get("content", "")

        except ApiException as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch query {query_name}: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process query {query_name}: {e}")

        model_ref = self._extract_model_ref(request.parameters)
        if not model_ref:
            raise HTTPException(status_code=422, detail="Query evaluation requires model configuration in parameters")

        target_name = response_target or actual_agent_name or "query-response"

        eval_request = EvaluationRequest(
            queryId=f"query-evaluation-{query_name}",
            input=input_text,
            responses=[Response(
                target=QueryTarget(type="agent", name=target_name),
                content=output_text
            )],
            query={"metadata": {"name": query_name, "namespace": query_namespace}, "spec": {"input": input_text}},
            modelRef=model_ref
        )

        golden_examples = self._extract_golden_examples(request.parameters)
        evaluator = LLMEvaluator(session=self.shared_session)

        result = await evaluator.evaluate(
            eval_request,
            EvaluationParameters.from_request_params(request.parameters or {}),
            golden_examples=golden_examples
        )

        if not result.metadata:
            result.metadata = {}
        result.metadata["query.name"] = query_name
        result.metadata["query.namespace"] = query_namespace
        if response_target:
            result.metadata["query.responseTarget"] = response_target

        return result
