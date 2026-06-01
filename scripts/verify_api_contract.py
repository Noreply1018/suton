from __future__ import annotations

import os
from pathlib import Path
import time
from typing import Any

from fastapi.testclient import TestClient

from app.config import settings
from app.db import connect
from app.main import app


PROJECT_FIELDS = {
    "id",
    "workspace_id",
    "name",
    "document_count",
    "question_count",
    "latest_status",
    "created_at",
    "updated_at",
}
DOCUMENT_FIELDS = {
    "id",
    "project_id",
    "filename",
    "content_type",
    "page_count",
    "extractable_page_count",
    "chunk_count",
    "text_quality",
    "text_quality_label",
    "searchable",
    "status",
    "processing_stage",
    "failed_stage",
    "failure_code",
    "failure_reason",
    "created_at",
    "processed_at",
    "updated_at",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_status(response: Any, status_code: int, detail: str | None = None) -> None:
    require(response.status_code == status_code, f"expected HTTP {status_code}, got {response.status_code}: {response.text}")
    if detail is not None:
        require(response.json()["detail"] == detail, f"expected detail {detail!r}, got {response.json()!r}")


def create_project_record(name: str) -> int:
    with connect() as conn:
        row = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (name,)).fetchone()
        conn.commit()
        return int(row["id"])


def create_document_record(project_id: int, **overrides: Any) -> int:
    values = {
        "filename": "contract.pdf",
        "content_type": "application/pdf",
        "storage_path": "uploads/contract.pdf",
        "page_count": 10,
        "extractable_page_count": 10,
        "chunk_count": 2,
        "text_quality": "good",
        "searchable": True,
        "status": "completed",
        "processing_stage": "completed",
        "failed_stage": None,
        "failure_code": None,
        "failure_reason": None,
    }
    values.update(overrides)
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage, failed_stage, failure_code, failure_reason
            )
            VALUES (
              %(project_id)s, %(filename)s, %(content_type)s, %(storage_path)s,
              %(page_count)s, %(extractable_page_count)s, %(chunk_count)s,
              %(text_quality)s, %(searchable)s, %(status)s, %(processing_stage)s,
              %(failed_stage)s, %(failure_code)s, %(failure_reason)s
            )
            RETURNING id
            """,
            {"project_id": project_id, **values},
        ).fetchone()
        conn.commit()
        return int(row["id"])


def project_updated_at(project_id: int):
    with connect() as conn:
        return conn.execute("SELECT updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()["updated_at"]


def assert_project_shape(project: dict[str, Any]) -> None:
    require(set(project) == PROJECT_FIELDS, f"project fields mismatch: {sorted(project)}")
    require(project["workspace_id"] == "local-default", "project workspace_id mismatch")
    require(isinstance(project["document_count"], int), "project document_count must be int")
    require(isinstance(project["question_count"], int), "project question_count must be int")
    require(project["latest_status"] in {"empty", "processing", "failed", "ready"}, "project latest_status mismatch")


def assert_document_shape(document: dict[str, Any]) -> None:
    require(set(document) == DOCUMENT_FIELDS, f"document fields mismatch: {sorted(document)}")
    require("storage_path" not in document, "document response leaked storage_path")
    labels = {"good": "良好", "fair": "一般", "poor": "不足", "unsearchable": "不可检索"}
    require(document["text_quality_label"] == labels[document["text_quality"]], "document text_quality_label mismatch")


def check_project_document_api() -> None:
    client = TestClient(app)
    suffix = time.time_ns()

    require_status(client.post("/projects", json={"name": " "}), 400, "项目名称不能为空")
    require_status(client.post("/projects", json={"name": "课" * 81}), 400, "项目名称不能超过 80 个字符")

    created = client.post("/projects", json={"name": f"合同项目-{suffix}"})
    require_status(created, 200)
    project = created.json()
    assert_project_shape(project)
    require(project["created_at"] is not None and project["updated_at"] is not None, "project timestamps must be present")
    project_id = int(project["id"])

    require_status(client.post("/projects", json={"name": f"合同项目-{suffix}"}), 409, "项目名称已存在")
    require_status(client.patch(f"/projects/{project_id}", json={"name": " "}), 400, "项目名称不能为空")
    require_status(client.patch(f"/projects/{project_id}", json={"name": "课" * 81}), 400, "项目名称不能超过 80 个字符")
    require_status(client.patch("/projects/999999999", json={"name": "不存在"}), 404, "项目不存在")

    with connect() as conn:
        conn.execute("UPDATE projects SET updated_at = now() - interval '2 days' WHERE id = %s", (project_id,))
        conn.commit()
    before_rename = project_updated_at(project_id)
    renamed = client.patch(f"/projects/{project_id}", json={"name": f"合同项目重命名-{suffix}"})
    require_status(renamed, 200)
    require(renamed.json()["name"] == f"合同项目重命名-{suffix}", "project rename did not persist")
    require(project_updated_at(project_id) > before_rename, "project rename did not update updated_at")

    with connect() as conn:
        conn.execute("UPDATE projects SET updated_at = '2001-01-01 00:00:00+00' WHERE id = %s", (project_id,))
        conn.commit()
    before_noop = project_updated_at(project_id)
    same_name = client.patch(f"/projects/{project_id}", json={"name": f"合同项目重命名-{suffix}"})
    require_status(same_name, 200)
    require(project_updated_at(project_id) == before_noop, "same-name project update changed updated_at")

    second_id = create_project_record(f"合同项目排序-{suffix}")
    third_id = create_project_record(f"合同项目排序同刻-{suffix}")
    with connect() as conn:
        conn.execute("UPDATE projects SET updated_at = now() - interval '1 day' WHERE id = %s", (project_id,))
        conn.execute("UPDATE projects SET updated_at = '2099-01-01 00:00:00+00' WHERE id IN (%s, %s)", (second_id, third_id))
        conn.commit()
    projects = client.get("/projects")
    require_status(projects, 200)
    assert_project_shape(projects.json()[0])
    require([item["id"] for item in projects.json()[:2]] == [third_id, second_id], "projects are not sorted by updated_at DESC, id DESC")

    read_before = project_updated_at(project_id)
    require_status(client.get(f"/projects/{project_id}"), 200)
    require_status(client.get("/projects"), 200)
    require(project_updated_at(project_id) == read_before, "read-only project queries changed updated_at")

    empty_project = client.get(f"/projects/{project_id}").json()
    require(empty_project["latest_status"] == "empty", "empty project latest_status mismatch")

    processing_project_id = create_project_record(f"合同处理中-{suffix}")
    create_document_record(
        processing_project_id,
        status="processing",
        processing_stage="embedding",
        page_count=0,
        extractable_page_count=0,
        searchable=False,
        text_quality="unsearchable",
        chunk_count=0,
    )
    require(client.get(f"/projects/{processing_project_id}").json()["latest_status"] == "processing", "processing latest_status mismatch")

    failed_project_id = create_project_record(f"合同失败-{suffix}")
    create_document_record(
        failed_project_id,
        status="failed",
        processing_stage="failed",
        page_count=0,
        extractable_page_count=0,
        failed_stage="embedding",
        failure_code="embedding_failed",
        failure_reason="生成 embedding 失败",
        searchable=False,
        text_quality="unsearchable",
        chunk_count=0,
    )
    require(client.get(f"/projects/{failed_project_id}").json()["latest_status"] == "failed", "failed latest_status mismatch")

    mixed_project_id = create_project_record(f"合同混合状态-{suffix}")
    create_document_record(
        mixed_project_id,
        status="failed",
        processing_stage="failed",
        page_count=0,
        extractable_page_count=0,
        failed_stage="embedding",
        failure_code="embedding_failed",
        failure_reason="生成 embedding 失败",
        searchable=False,
        text_quality="unsearchable",
        chunk_count=0,
    )
    create_document_record(
        mixed_project_id,
        status="processing",
        processing_stage="embedding",
        page_count=0,
        extractable_page_count=0,
        searchable=False,
        text_quality="unsearchable",
        chunk_count=0,
    )
    require(client.get(f"/projects/{mixed_project_id}").json()["latest_status"] == "processing", "latest_status priority mismatch")

    ready_project_id = create_project_record(f"合同就绪-{suffix}")
    document_id = create_document_record(ready_project_id)
    require(client.get(f"/projects/{ready_project_id}").json()["latest_status"] == "ready", "ready latest_status mismatch")

    documents = client.get(f"/projects/{ready_project_id}/documents")
    require_status(documents, 200)
    require(len(documents.json()) == 1, "document list length mismatch")
    assert_document_shape(documents.json()[0])

    older_document_id = create_document_record(ready_project_id, filename="older.pdf")
    newer_document_id = create_document_record(ready_project_id, filename="newer.pdf")
    with connect() as conn:
        conn.execute("UPDATE documents SET created_at = '2099-01-01 00:00:00+00' WHERE id IN (%s, %s)", (older_document_id, newer_document_id))
        conn.execute("UPDATE documents SET created_at = '2001-01-01 00:00:00+00' WHERE id = %s", (document_id,))
        conn.commit()
    sorted_documents = client.get(f"/projects/{ready_project_id}/documents")
    require_status(sorted_documents, 200)
    require(
        [item["id"] for item in sorted_documents.json()[:2]] == [newer_document_id, older_document_id],
        "documents are not sorted by created_at DESC, id DESC",
    )

    document = client.get(f"/documents/{document_id}")
    require_status(document, 200)
    assert_document_shape(document.json())
    require(document.json()["id"] == document_id, "document detail id mismatch")
    with connect() as conn:
        conn.execute("UPDATE projects SET updated_at = '2001-01-01 00:00:00+00' WHERE id = %s", (ready_project_id,))
        conn.commit()
    before_document_reads = project_updated_at(ready_project_id)
    require_status(client.get(f"/projects/{ready_project_id}/documents"), 200)
    require_status(client.get(f"/documents/{document_id}"), 200)
    require(project_updated_at(ready_project_id) == before_document_reads, "read-only document queries changed project updated_at")
    require_status(client.get("/documents/999999999"), 404, "资料不存在")
    require_status(client.get("/projects/999999999/documents"), 404, "项目不存在")
    missing_file_document_id = create_document_record(ready_project_id, storage_path=f"uploads/missing-{suffix}.pdf")
    require_status(client.get(f"/documents/{missing_file_document_id}/file"), 404, "资料文件不存在")

    require_status(
        client.post(
            f"/projects/{ready_project_id}/documents",
            files={"file": ("not-pdf.txt", b"not a pdf", "text/plain")},
        ),
        400,
        "v0.2.0 只支持上传 PDF 文件",
    )
    require_status(
        client.post(
            f"/projects/{ready_project_id}/documents",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        ),
        400,
        "上传文件不能为空",
    )

    blocker = Path("tmp") / f"upload-blocker-{suffix}"
    blocker.parent.mkdir(parents=True, exist_ok=True)
    blocker.write_text("not a directory", encoding="utf-8")
    original_upload_dir = settings.upload_dir
    try:
        object.__setattr__(settings, "upload_dir", str(blocker))
        require_status(
            client.post(
                f"/projects/{ready_project_id}/documents",
                files={"file": ("save-failure.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
            ),
            500,
            "资料文件保存失败",
        )
    finally:
        object.__setattr__(settings, "upload_dir", original_upload_dir)
        blocker.unlink(missing_ok=True)

    with connect() as conn:
        conn.execute("UPDATE projects SET updated_at = '2001-01-01 00:00:00+00' WHERE id = %s", (ready_project_id,))
        conn.commit()
    before_upload = project_updated_at(ready_project_id)
    uploaded = client.post(
        f"/projects/{ready_project_id}/documents",
        files={"file": (f"uploaded-{suffix}.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
    )
    require_status(uploaded, 200)
    assert_document_shape(uploaded.json())
    require(uploaded.json()["status"] == "uploaded", "uploaded document status mismatch")
    require(project_updated_at(ready_project_id) > before_upload, "document upload did not update project updated_at")


def main() -> None:
    check = os.getenv("CHECK", "v020-project-document-api")
    checks = {
        "v020-project-document-api": check_project_document_api,
    }
    if check not in checks:
        raise SystemExit(f"unsupported CHECK={check}")
    checks[check]()
    print(f"CHECK={check} passed")


if __name__ == "__main__":
    main()
