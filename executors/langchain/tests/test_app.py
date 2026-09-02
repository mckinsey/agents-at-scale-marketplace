"""Tests for langchain_executor.app."""

from starlette.applications import Starlette

from langchain_executor.app import create_app


def test_create_app_returns_starlette_instance():
    app = create_app()

    assert isinstance(app, Starlette)
