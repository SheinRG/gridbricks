from fastapi.testclient import TestClient

from app.main import create_app


def test_health_ok():
    client = TestClient(create_app())
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "X-Response-Time" in res.headers
