import pytest
from fastapi.testclient import TestClient
from evaluator.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    from httpx import AsyncClient, ASGITransport
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
