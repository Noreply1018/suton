from fastapi.testclient import TestClient

from app.main import app


def test_create_project_requires_name() -> None:
    client = TestClient(app)
    response = client.post("/projects", json={"name": " "})
    assert response.status_code == 400
    assert response.json()["detail"] == "项目名称不能为空"


def test_create_question_requires_text() -> None:
    client = TestClient(app)
    response = client.post("/projects/1/questions", json={"text": " "})
    assert response.status_code == 400
    assert response.json()["detail"] == "题目不能为空"


def test_upload_rejects_non_pdf_extension() -> None:
    client = TestClient(app)
    response = client.post(
        "/projects/1/documents",
        files={"file": ("not-pdf.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "v0.1.0 只支持上传 PDF 文件"


def test_upload_rejects_pdf_name_with_wrong_content_type() -> None:
    client = TestClient(app)
    response = client.post(
        "/projects/1/documents",
        files={"file": ("fake.pdf", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "v0.1.0 只支持上传 PDF 文件"
