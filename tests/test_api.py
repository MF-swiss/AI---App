from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


client = TestClient(app)
headers = {"X-API-Key": settings.app_api_key}


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_requires_api_key():
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "Hi"}]})
    assert response.status_code == 401


def test_context_files_requires_api_key():
    response = client.get("/context/files")
    assert response.status_code == 401


def test_context_read_requires_api_key():
    response = client.post("/context/read", json={"paths": ["app/main.py"]})
    assert response.status_code == 401


def test_execute_requires_api_key():
    response = client.post("/execute", json={"language": "python", "code": "print('ok')"})
    assert response.status_code == 401
