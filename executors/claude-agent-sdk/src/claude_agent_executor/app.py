from ark_sdk.executor_app import ExecutorApp
from starlette.applications import Starlette
from .executor import ClaudeAgentExecutor

executor = ClaudeAgentExecutor()
app_instance = ExecutorApp(
    executor,
    "ClaudeAgentSDK",
    description="Claude Agent SDK executor with built-in tool access and session persistence",
)


def create_app() -> Starlette:
    return app_instance.create_app()
