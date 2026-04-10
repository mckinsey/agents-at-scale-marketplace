import logging

from ark_sdk.executor import ExecutionEngineRequest, ExecutionEngineResponse
from ark_sdk.executor_app import ExecutorApp
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .executor import OpenAIResponsesExecutor

logger = logging.getLogger(__name__)

executor = OpenAIResponsesExecutor()
app_instance = ExecutorApp(
    executor,
    "OpenAIResponses",
)


async def _execute(request: Request) -> JSONResponse:
    """Direct REST endpoint for local testing and SDK-version compatibility.

    Accepts ExecutionEngineRequest JSON and returns ExecutionEngineResponse JSON,
    bypassing the A2A layer. Useful when the A2A adapter does not yet propagate
    agent.annotations / query_annotations / execution_engine_annotations.
    """
    try:
        body = await request.json()
        req = ExecutionEngineRequest(**body)
        messages = await executor.execute_agent(req)
        return JSONResponse(ExecutionEngineResponse(messages=messages).model_dump())
    except Exception as exc:
        logger.error("Direct execute failed: %s", exc, exc_info=True)
        return JSONResponse(
            ExecutionEngineResponse(messages=[], error=str(exc)).model_dump(),
            status_code=500,
        )


def create_app() -> Starlette:
    app = app_instance.create_app()
    app.routes.insert(0, Route("/execute", _execute, methods=["POST"]))
    return app
