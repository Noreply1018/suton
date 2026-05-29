from fastapi.testclient import TestClient

from app.main import app


def test_create_project_requires_name() -> None:
    client = TestClient(app)
    response = client.post("/projects", json={"name": " "})
    assert response.status_code == 400
    assert response.json()["detail"] == "项目名称不能为空"
