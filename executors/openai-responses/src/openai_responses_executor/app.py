from ark_sdk.executor_app import ExecutorApp
from starlette.applications import Starlette
from .executor import OpenAIResponsesExecutor

executor = OpenAIResponsesExecutor()
app_instance = ExecutorApp(
    executor,
    "OpenAIResponses",
)


def create_app() -> Starlette:
    return app_instance.create_app()
