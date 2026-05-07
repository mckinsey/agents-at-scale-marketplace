import logging

from ark_sdk.executor import ExecutionEngineRequest, ExecutionEngineResponse
from ark_sdk.executor_app import ExecutorApp
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .executor import OpenAIFileInputsExecutor
from .file_api import file_api_routes

logger = logging.getLogger(__name__)

executor = OpenAIFileInputsExecutor()
app_instance = ExecutorApp(
    executor,
    "OpenAIFileInputs",
)


async def _execute(request: Request) -> JSONResponse:
    """Direct REST endpoint for local testing and SDK-version compatibility."""
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
    for route in file_api_routes:
        app.routes.insert(0, route)
    return app
