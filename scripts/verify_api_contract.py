from __future__ import annotations

import os
from pathlib import Path
import time
from typing import Any

from fastapi.testclient import TestClient

from app.config import settings
from app.db import connect, vector_literal
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
QUESTION_HISTORY_FIELDS = {
    "id",
    "project_id",
    "text",
    "status",
    "failure_code",
    "failure_reason",
    "last_search_at",
    "updated_at",
    "match_count",
    "top_confidence_level",
    "top_confidence_label",
}
QUESTION_DETAIL_FIELDS = {
    "id",
    "project_id",
    "text",
    "status",
    "failure_code",
    "failure_reason",
    "last_search_at",
    "created_at",
    "updated_at",
    "matches",
}
QUESTION_MATCH_FIELDS = {
    "id",
    "question_id",
    "document_id",
    "document_filename",
    "page_no",
    "chunk_id",
    "score",
    "rank",
    "confidence_level",
    "confidence_label",
    "hit_reason",
    "source_text",
    "context_before",
    "context_after",
    "pdf_url",
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


def delete_project_records(project_ids: list[int]) -> None:
    if not project_ids:
        return
    with connect() as conn:
        conn.execute("DELETE FROM projects WHERE id = ANY(%s)", (project_ids,))
        conn.commit()


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


def check_project_name_limits() -> None:
    client = TestClient(app)
    suffix = str(time.time_ns())
    created_ids: list[int] = []

    def remember(response: Any) -> int:
        project_id = int(response.json()["id"])
        created_ids.append(project_id)
        return project_id

    try:
        require_status(client.post("/projects", json={"name": "   "}), 400, "项目名称不能为空")
        require_status(client.post("/projects", json={"name": "课" * 81}), 400, "项目名称不能超过 80 个字符")

        base_name = f"边界项目-{suffix}"
        trimmed = client.post("/projects", json={"name": f"  {base_name}  "})
        require_status(trimmed, 200)
        trimmed_id = remember(trimmed)
        require(trimmed.json()["name"] == base_name, "project create did not trim name")
        assert_project_shape(trimmed.json())

        duplicate = client.post("/projects", json={"name": base_name})
        require_status(duplicate, 409, "项目名称已存在")

        legal_prefix = f"合法80-{suffix}-"
        legal_80 = legal_prefix + ("界" * (80 - len(legal_prefix)))
        require(len(legal_80) == 80, "legal project name fixture is not 80 characters")
        legal = client.post("/projects", json={"name": legal_80})
        require_status(legal, 200)
        legal_id = remember(legal)
        require(legal.json()["name"] == legal_80, "80-character project name was not preserved")

        rename_empty = client.patch(f"/projects/{legal_id}", json={"name": " "})
        require_status(rename_empty, 400, "项目名称不能为空")
        rename_too_long = client.patch(f"/projects/{legal_id}", json={"name": "项" * 81})
        require_status(rename_too_long, 400, "项目名称不能超过 80 个字符")
        rename_duplicate = client.patch(f"/projects/{legal_id}", json={"name": base_name})
        require_status(rename_duplicate, 409, "项目名称已存在")

        renamed_name = f"重命名边界-{suffix}"
        renamed = client.patch(f"/projects/{legal_id}", json={"name": f" {renamed_name} "})
        require_status(renamed, 200)
        require(renamed.json()["name"] == renamed_name, "project rename did not trim name")

        require_status(client.patch("/projects/999999999", json={"name": "不存在"}), 404, "项目不存在")
        require_status(client.post("/projects", json={"name": base_name}), 409, "项目名称已存在")
        require_status(client.patch(f"/projects/{trimmed_id}", json={"name": renamed_name}), 409, "项目名称已存在")
    finally:
        delete_project_records(created_ids)


def check_document_detail_fields() -> None:
    client = TestClient(app)
    suffix = time.time_ns()
    project_id = create_project_record(f"资料详情字段-{suffix}")
    try:
        completed_id = create_document_record(
            project_id,
            filename="completed-detail.pdf",
            status="completed",
            processing_stage="completed",
            page_count=10,
            extractable_page_count=10,
            chunk_count=2,
            text_quality="good",
            searchable=True,
        )
        failed_id = create_document_record(
            project_id,
            filename="failed-detail.pdf",
            status="failed",
            processing_stage="failed",
            failed_stage="embedding",
            failure_code="embedding_failed",
            failure_reason="生成 embedding 失败",
            page_count=10,
            extractable_page_count=10,
            chunk_count=0,
            text_quality="good",
            searchable=False,
        )
        unsupported_id = create_document_record(
            project_id,
            filename="unsupported-detail.pdf",
            status="unsupported",
            processing_stage="failed",
            failed_stage="extracting_text",
            failure_code="no_text_layer",
            failure_reason="PDF 无可提取文字层，v0.2.0 不进入 OCR",
            page_count=4,
            extractable_page_count=0,
            chunk_count=0,
            text_quality="unsearchable",
            searchable=False,
        )

        completed = client.get(f"/documents/{completed_id}")
        require_status(completed, 200)
        assert_document_shape(completed.json())
        require(completed.json()["filename"] == "completed-detail.pdf", "completed document filename mismatch")
        require(completed.json()["failure_code"] is None, "completed document failure_code must be null")
        require(completed.json()["failure_reason"] is None, "completed document failure_reason must be null")
        require(completed.json()["text_quality_label"] == "良好", "completed document text_quality_label mismatch")
        require(completed.json()["searchable"] is True, "completed document searchable mismatch")

        failed = client.get(f"/documents/{failed_id}")
        require_status(failed, 200)
        assert_document_shape(failed.json())
        require(failed.json()["status"] == "failed", "failed document status mismatch")
        require(failed.json()["failed_stage"] == "embedding", "failed document failed_stage mismatch")
        require(failed.json()["failure_code"] == "embedding_failed", "failed document failure_code mismatch")
        require(failed.json()["failure_reason"] == "生成 embedding 失败", "failed document failure_reason mismatch")
        require(failed.json()["searchable"] is False, "failed document searchable mismatch")

        unsupported = client.get(f"/documents/{unsupported_id}")
        require_status(unsupported, 200)
        assert_document_shape(unsupported.json())
        require(unsupported.json()["status"] == "unsupported", "unsupported document status mismatch")
        require(unsupported.json()["failed_stage"] == "extracting_text", "unsupported document failed_stage mismatch")
        require(unsupported.json()["failure_code"] == "no_text_layer", "unsupported document failure_code mismatch")
        require(unsupported.json()["failure_reason"] == "PDF 无可提取文字层，v0.2.0 不进入 OCR", "unsupported document failure_reason mismatch")
        require(unsupported.json()["text_quality_label"] == "不可检索", "unsupported document text_quality_label mismatch")
        require(unsupported.json()["searchable"] is False, "unsupported document searchable mismatch")

        documents = client.get(f"/projects/{project_id}/documents")
        require_status(documents, 200)
        for document in documents.json():
            assert_document_shape(document)
            require("storage_path" not in document, "document list leaked storage_path")
    finally:
        delete_project_records([project_id])


def check_document_scope_disabled() -> None:
    client = TestClient(app)
    suffix = time.time_ns()
    project_id = create_project_record(f"不可检索资料范围-{suffix}")
    try:
        searchable_id = create_document_record(
            project_id,
            filename="scope-searchable.pdf",
            status="completed",
            processing_stage="completed",
            searchable=True,
            chunk_count=1,
            text_quality="good",
        )
        failed_id = create_document_record(
            project_id,
            filename="scope-failed.pdf",
            status="failed",
            processing_stage="failed",
            failed_stage="embedding",
            failure_code="embedding_failed",
            failure_reason="生成 embedding 失败",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        unsupported_id = create_document_record(
            project_id,
            filename="scope-unsupported.pdf",
            status="unsupported",
            processing_stage="failed",
            failed_stage="extracting_text",
            failure_code="no_text_layer",
            failure_reason="PDF 无可提取文字层，v0.2.0 不进入 OCR",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        no_chunk_id = create_document_record(
            project_id,
            filename="scope-no-chunk.pdf",
            status="completed",
            processing_stage="completed",
            searchable=False,
            chunk_count=0,
            text_quality="good",
        )

        for document_id in [failed_id, unsupported_id, no_chunk_id]:
            response = client.post(
                f"/projects/{project_id}/questions",
                json={"text": f"不可检索资料 {document_id}", "document_ids": [document_id]},
            )
            require_status(response, 400, "检索范围包含不可用资料")

        mixed = client.post(
            f"/projects/{project_id}/questions",
            json={"text": "混合可检索与不可检索资料", "document_ids": [searchable_id, failed_id]},
        )
        require_status(mixed, 400, "检索范围包含不可用资料")
    finally:
        delete_project_records([project_id])


def check_question_scope_errors() -> None:
    client = TestClient(app)
    suffix = time.time_ns()
    project_id = create_project_record(f"题目范围错误-{suffix}")
    other_project_id = create_project_record(f"题目范围跨项目-{suffix}")
    no_searchable_project_id: int | None = None
    try:
        searchable_id = create_document_record(
            project_id,
            filename="searchable-scope.pdf",
            status="completed",
            processing_stage="completed",
            searchable=True,
            chunk_count=1,
            text_quality="good",
        )
        processing_id = create_document_record(
            project_id,
            filename="processing-scope.pdf",
            status="processing",
            processing_stage="embedding",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        unsearchable_id = create_document_record(
            project_id,
            filename="unsearchable-scope.pdf",
            status="completed",
            processing_stage="completed",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        other_document_id = create_document_record(
            other_project_id,
            filename="other-project-scope.pdf",
            status="completed",
            processing_stage="completed",
            searchable=True,
            chunk_count=1,
            text_quality="good",
        )
        empty_scope = client.post(
            f"/projects/{project_id}/questions",
            json={"text": "题目范围为空", "document_ids": []},
        )
        require_status(empty_scope, 400, "检索范围不能为空")

        cross_project = client.post(
            f"/projects/{project_id}/questions",
            json={"text": "题目范围跨项目", "document_ids": [other_document_id]},
        )
        require_status(cross_project, 400, "检索范围包含不可用资料")

        processing_scope = client.post(
            f"/projects/{project_id}/questions",
            json={"text": "题目范围包含处理中资料", "document_ids": [processing_id]},
        )
        require_status(processing_scope, 400, "检索范围包含不可用资料")

        unsearchable_scope = client.post(
            f"/projects/{project_id}/questions",
            json={"text": "题目范围包含不可检索资料", "document_ids": [unsearchable_id]},
        )
        require_status(unsearchable_scope, 400, "检索范围包含不可用资料")

        mixed_scope = client.post(
            f"/projects/{project_id}/questions",
            json={"text": "题目范围混合资料", "document_ids": [searchable_id, unsearchable_id]},
        )
        require_status(mixed_scope, 400, "检索范围包含不可用资料")

        no_searchable_project_id = create_project_record(f"题目范围无可检索-{suffix}")
        create_document_record(
            no_searchable_project_id,
            filename="no-searchable-scope.pdf",
            status="failed",
            processing_stage="failed",
            failed_stage="embedding",
            failure_code="embedding_failed",
            failure_reason="生成 embedding 失败",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        no_searchable = client.post(
            f"/projects/{no_searchable_project_id}/questions",
            json={"text": "没有可检索资料", "document_ids": None},
        )
        require_status(no_searchable, 409, "需先上传并处理资料")

        missing_project = client.post(
            "/projects/999999999/questions",
            json={"text": "项目不存在", "document_ids": None},
        )
        require_status(missing_project, 404, "项目不存在")
    finally:
        project_ids = [project_id, other_project_id]
        if no_searchable_project_id is not None:
            project_ids.append(no_searchable_project_id)
        delete_project_records(project_ids)


def check_question_history_api() -> None:
    client = TestClient(app)
    suffix = time.time_ns()
    project_id = create_project_record(f"题目历史接口-{suffix}")
    other_project_id = create_project_record(f"题目历史隔离-{suffix}")
    try:
        with connect() as conn:
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, 'question-history.pdf', 'application/pdf', 'uploads/question-history.pdf', 1, 1, 2, 'good', true, 'completed', 'completed')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            page = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, 1, 'alpha beta gamma', 'alpha beta gamma', 16)
                RETURNING id
                """,
                (document["id"],),
            ).fetchone()
            chunk = conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char,
                  embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, 1, 'alpha', 0, 5, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-question-history-api')
                RETURNING id
                """,
                (document["id"], page["id"], vector_literal([1.0] + [0.0] * 1023)),
            ).fetchone()
            older_question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'older question', 'completed', '2001-01-01 00:00:00+00', '2001-01-01 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            newer_question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'newer question', 'completed', '2099-01-01 00:00:00+00', '2099-01-01 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            no_source_question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'no source question', 'no_reliable_source', '2005-01-01 00:00:00+00', '2005-01-01 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            failed_question = conn.execute(
                """
                INSERT INTO questions (
                  project_id, text, status, failure_code, failure_reason, last_search_at, updated_at
                )
                VALUES (%s, 'failed question', 'failed', 'search_failed', '题目检索失败', '2004-01-01 00:00:00+00', '2004-01-01 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'other project question', 'completed', '2100-01-01 00:00:00+00', '2100-01-01 00:00:00+00')
                """,
                (other_project_id,),
            )
            for question_id, score, rank, level in [
                (older_question["id"], 0.88, 1, "strong"),
                (newer_question["id"], 0.61, 1, "reference"),
                (newer_question["id"], 0.44, 2, "low"),
            ]:
                conn.execute(
                    """
                    INSERT INTO question_matches (
                      question_id, chunk_id, document_id, page_no, score, rank,
                      confidence_level, hit_reason, source_text, context_before, context_after
                    )
                    VALUES (%s, %s, %s, 1, %s, %s, %s, 'history fixture', 'alpha', '', ' beta gamma')
                    """,
                    (question_id, chunk["id"], document["id"], score, rank, level),
                )
            conn.commit()

        missing_project = client.get("/projects/999999999/questions")
        require_status(missing_project, 404, "项目不存在")

        history = client.get(f"/projects/{project_id}/questions")
        require_status(history, 200)
        rows = history.json()
        require(len(rows) == 4, f"question history length mismatch: {rows!r}")
        for row in rows:
            require(set(row) == QUESTION_HISTORY_FIELDS, f"question history fields mismatch: {sorted(row)}")
            require(row["project_id"] == project_id, "question history leaked another project")

        require([row["id"] for row in rows] == [newer_question["id"], no_source_question["id"], failed_question["id"], older_question["id"]], "question history sort mismatch")
        require(rows[0]["match_count"] == 2, "newer question match_count mismatch")
        require(rows[0]["top_confidence_level"] == "reference", "newer question top confidence mismatch")
        require(rows[0]["top_confidence_label"] == "可参考", "newer question top confidence label mismatch")
        require(rows[1]["status"] == "no_reliable_source", "no-source question status mismatch")
        require(rows[1]["match_count"] == 0, "no-source question match_count mismatch")
        require(rows[1]["top_confidence_level"] is None, "no-source top confidence must be null")
        require(rows[1]["top_confidence_label"] == "无可靠来源", "no-source top confidence label mismatch")
        require(rows[2]["failure_code"] == "search_failed", "failed question failure_code mismatch")
        require(rows[2]["failure_reason"] == "题目检索失败", "failed question failure_reason mismatch")
        require(rows[3]["match_count"] == 1, "older question match_count mismatch")
        require(rows[3]["top_confidence_level"] == "strong", "older question top confidence mismatch")
        require(rows[3]["top_confidence_label"] == "强相关", "older question top confidence label mismatch")
    finally:
        delete_project_records([project_id, other_project_id])


def check_question_detail_api() -> None:
    client = TestClient(app)
    suffix = time.time_ns()
    project_id = create_project_record(f"题目详情接口-{suffix}")
    try:
        with connect() as conn:
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, 'question-detail.pdf', 'application/pdf', 'uploads/question-detail.pdf', 1, 1, 1, 'good', true, 'completed', 'completed')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            page = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, 1, 'before answer after', 'before answer after', 19)
                RETURNING id
                """,
                (document["id"],),
            ).fetchone()
            chunk = conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char,
                  embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, 1, 'answer', 7, 13, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-question-detail-api')
                RETURNING id
                """,
                (document["id"], page["id"], vector_literal([1.0] + [0.0] * 1023)),
            ).fetchone()
            completed_question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'completed detail question', 'completed', '2099-01-01 00:00:00+00', '2099-01-01 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            no_source_question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'no source detail question', 'no_reliable_source', '2099-01-02 00:00:00+00', '2099-01-02 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            failed_question = conn.execute(
                """
                INSERT INTO questions (
                  project_id, text, status, failure_code, failure_reason, last_search_at, updated_at
                )
                VALUES (%s, 'failed detail question', 'failed', 'source_context_failed', '来源上下文生成失败', '2099-01-03 00:00:00+00', '2099-01-03 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            match = conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, 0.82, 1, 'strong', 'question detail fixture', 'answer', 'before ', ' after')
                RETURNING id
                """,
                (completed_question["id"], chunk["id"], document["id"]),
            ).fetchone()
            conn.commit()

        missing_question = client.get("/questions/999999999")
        require_status(missing_question, 404, "题目不存在")

        completed = client.get(f"/questions/{completed_question['id']}")
        require_status(completed, 200)
        completed_body = completed.json()
        require(set(completed_body) == QUESTION_DETAIL_FIELDS, f"question detail fields mismatch: {sorted(completed_body)}")
        require(completed_body["id"] == completed_question["id"], "question detail id mismatch")
        require(completed_body["project_id"] == project_id, "question detail project_id mismatch")
        require(completed_body["status"] == "completed", "completed question status mismatch")
        require(completed_body["failure_code"] is None, "completed question failure_code must be null")
        require(completed_body["failure_reason"] is None, "completed question failure_reason must be null")
        require(len(completed_body["matches"]) == 1, "completed question match count mismatch")
        completed_match = completed_body["matches"][0]
        require(set(completed_match) == QUESTION_MATCH_FIELDS, f"question match fields mismatch: {sorted(completed_match)}")
        require(completed_match["id"] == match["id"], "question match id mismatch")
        require(completed_match["question_id"] == completed_question["id"], "question match question_id mismatch")
        require(completed_match["document_id"] == document["id"], "question match document_id mismatch")
        require(completed_match["document_filename"] == "question-detail.pdf", "question match document_filename mismatch")
        require(completed_match["page_no"] == 1, "question match page_no mismatch")
        require(completed_match["chunk_id"] == chunk["id"], "question match chunk_id mismatch")
        require(completed_match["confidence_level"] == "strong", "question match confidence_level mismatch")
        require(completed_match["confidence_label"] == "强相关", "question match confidence_label mismatch")
        require(completed_match["source_text"] == "answer", "question match source_text mismatch")
        require(completed_match["context_before"] == "before ", "question match context_before mismatch")
        require(completed_match["context_after"] == " after", "question match context_after mismatch")
        require(completed_match["pdf_url"] == f"/documents/{document['id']}/file#page=1", "question match pdf_url mismatch")
        require("filename" not in completed_match, "question match leaked legacy filename field")

        no_source = client.get(f"/questions/{no_source_question['id']}")
        require_status(no_source, 200)
        no_source_body = no_source.json()
        require(set(no_source_body) == QUESTION_DETAIL_FIELDS, f"no-source question fields mismatch: {sorted(no_source_body)}")
        require(no_source_body["status"] == "no_reliable_source", "no-source question status mismatch")
        require(no_source_body["failure_code"] is None, "no-source failure_code must be null")
        require(no_source_body["failure_reason"] is None, "no-source failure_reason must be null")
        require(no_source_body["matches"] == [], "no-source matches must be empty")

        failed = client.get(f"/questions/{failed_question['id']}")
        require_status(failed, 200)
        failed_body = failed.json()
        require(set(failed_body) == QUESTION_DETAIL_FIELDS, f"failed question fields mismatch: {sorted(failed_body)}")
        require(failed_body["status"] == "failed", "failed question status mismatch")
        require(failed_body["failure_code"] == "source_context_failed", "failed question failure_code mismatch")
        require(failed_body["failure_reason"] == "来源上下文生成失败", "failed question failure_reason mismatch")
        require(failed_body["matches"] == [], "failed question matches must be empty")
    finally:
        delete_project_records([project_id])


def check_stale_source() -> None:
    client = TestClient(app)
    suffix = time.time_ns()
    project_id = create_project_record(f"失效来源-{suffix}")
    page_text = "before stale source after"
    source_text = "stale source"
    source_start = page_text.index(source_text)
    query = [1.0, 0.0] + [0.0] * 1022
    try:
        with connect() as conn:
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, 'stale-source.pdf', 'application/pdf', 'uploads/stale-source.pdf', 1, 1, 1, 'good', true, 'completed', 'completed')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            page = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, 1, %s, %s, %s)
                RETURNING id
                """,
                (document["id"], page_text, page_text, len(page_text)),
            ).fetchone()
            chunk = conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char,
                  embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-stale-source')
                RETURNING id
                """,
                (
                    document["id"],
                    page["id"],
                    source_text,
                    source_start,
                    source_start + len(source_text),
                    vector_literal(query),
                ),
            ).fetchone()
            question = conn.execute(
                "INSERT INTO questions (project_id, text, status) VALUES (%s, 'stale source query', 'completed') RETURNING id",
                (project_id,),
            ).fetchone()
            match = conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, 0.88, 1, 'strong', 'fixed stale source fixture', %s, 'before ', ' after')
                RETURNING id
                """,
                (question["id"], chunk["id"], document["id"], source_text),
            ).fetchone()
            conn.commit()

        available = client.get(f"/questions/{question['id']}/matches/{match['id']}")
        require_status(available, 200)
        require(available.json()["source_text"] == source_text, "available source detail source_text mismatch")

        with connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = 'processing', processing_stage = 'embedding', searchable = false, updated_at = now()
                WHERE id = %s
                """,
                (document["id"],),
            )
            conn.commit()

        stale = client.get(f"/questions/{question['id']}/matches/{match['id']}")
        require_status(stale, 404, "来源已失效")
    finally:
        delete_project_records([project_id])


def main() -> None:
    check = os.getenv("CHECK", "v020-project-document-api")
    checks = {
        "v020-project-document-api": check_project_document_api,
        "v020-document-detail-fields": check_document_detail_fields,
        "v020-document-scope-disabled": check_document_scope_disabled,
        "v020-project-name-limits": check_project_name_limits,
        "v020-question-scope-errors": check_question_scope_errors,
        "v020-question-history-api": check_question_history_api,
        "v020-question-detail-api": check_question_detail_api,
        "v020-stale-source": check_stale_source,
    }
    if check not in checks:
        raise SystemExit(f"unsupported CHECK={check}")
    checks[check]()
    print(f"CHECK={check} passed")


if __name__ == "__main__":
    main()
