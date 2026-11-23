from fastapi.testclient import TestClient

from app.main import app
client = TestClient(app)


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_accepts_no_browser_api_key():
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "Hi"}]})
    assert response.status_code in (200, 500)


def test_context_files_is_available_to_the_web_app():
    response = client.get("/context/files")
    assert response.status_code == 200


def test_context_read_is_available_to_the_web_app():
    response = client.post("/context/read", json={"paths": ["app/main.py"]})
    assert response.status_code == 200


def test_execute_accepts_no_browser_api_key():
    response = client.post("/execute", json={"language": "python", "code": "print('ok')"})
    assert response.status_code in (200, 503)
