from fastapi.testclient import TestClient

from deeptutor.api.routers.fusion_test_app import create_app


def test_isolated_fusion_app_requires_test_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    client = TestClient(create_app())
    assert client.get("/openapi.json").status_code == 200
