from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.db import connect
from app.processing import create_uploaded_document, queue_process_document, search_question

app = FastAPI(title="Suton v0.1.0 API")
logger = logging.getLogger(__name__)

TEXT_QUALITY_LABELS = {
    "good": "良好",
    "fair": "一般",
    "poor": "不足",
    "unsearchable": "不可检索",
}
CONFIDENCE_LABELS = {
    "strong": "强相关",
    "reference": "可参考",
    "low": "低置信",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/projects")
def list_projects() -> list[dict]:
    with connect() as conn:
        return conn.execute(
            project_select_sql() + " ORDER BY p.updated_at DESC, p.id DESC"
        ).fetchall()


@app.post("/projects")
def create_project(payload: dict[str, str]) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="项目名称不能超过 80 个字符")
    with connect() as conn:
        try:
            row = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (name,)).fetchone()
            conn.commit()
        except Exception as exc:
            conn.rollback()
            if getattr(exc, "sqlstate", "") == "23505":
                raise HTTPException(status_code=409, detail="项目名称已存在") from exc
            raise
    return get_project(row["id"])


@app.get("/projects/{project_id}")
def get_project(project_id: int) -> dict:
    with connect() as conn:
        project = conn.execute(
            project_select_sql("WHERE p.id = %s"),
            (project_id,),
        ).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        return project


@app.patch("/projects/{project_id}")
def update_project(project_id: int, payload: dict[str, str]) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="项目名称不能超过 80 个字符")
    with connect() as conn:
        current = conn.execute("SELECT name FROM projects WHERE id = %s", (project_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="项目不存在")
        if current["name"] == name:
            return get_project(project_id)
        try:
            conn.execute("UPDATE projects SET name = %s, updated_at = now() WHERE id = %s", (name, project_id))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            if getattr(exc, "sqlstate", "") == "23505":
                raise HTTPException(status_code=409, detail="项目名称已存在") from exc
            raise
    return get_project(project_id)


@app.get("/projects/{project_id}/documents")
def list_documents(project_id: int) -> list[dict]:
    with connect() as conn:
        project = conn.execute("SELECT id FROM projects WHERE id = %s", (project_id,)).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        rows = conn.execute(document_select_sql("WHERE project_id = %s") + " ORDER BY created_at DESC, id DESC", (project_id,)).fetchall()
        return [document_response(row) for row in rows]


@app.get("/documents/{document_id}")
def get_document(document_id: int) -> dict:
    with connect() as conn:
        document = conn.execute(document_select_sql("WHERE id = %s"), (document_id,)).fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="资料不存在")
    return document_response(document)


@app.delete("/documents/{document_id}")
def delete_document(document_id: int) -> dict:
    delete_document_with_files(document_id)
    return {"deleted": True, "document_id": document_id}


@app.post("/projects/{project_id}/documents")
def upload_document(project_id: int, file: UploadFile = File(...)) -> dict:
    if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="v0.2.0 只支持上传 PDF 文件")
    upload_root = Path(settings.upload_dir)
    with connect() as conn:
        project = conn.execute("SELECT id FROM projects WHERE id = %s", (project_id,)).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    safe_name = Path(file.filename).name
    storage_path = upload_root / f"project-{project_id}-{safe_name}"
    try:
        upload_root.mkdir(parents=True, exist_ok=True)
        with storage_path.open("wb") as output:
            shutil.copyfileobj(file.file, output)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="资料文件保存失败") from exc
    if storage_path.stat().st_size == 0:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    document_id = create_uploaded_document(project_id, safe_name, "application/pdf", str(storage_path))
    queue_process_document(document_id)
    return get_document(document_id)


def delete_document_with_files(document_id: int) -> None:
    upload_root = Path(settings.upload_dir).resolve()
    trash_dir: Path | None = None
    moved_files: list[tuple[Path, Path]] = []
    try:
        with connect() as conn:
            with conn.transaction():
                document = conn.execute(
                    "SELECT id, project_id, storage_path FROM documents WHERE id = %s FOR UPDATE",
                    (document_id,),
                ).fetchone()
                if not document:
                    raise HTTPException(status_code=404, detail="资料不存在")

                txid = conn.execute("SELECT txid_current() AS value").fetchone()["value"]
                trash_dir = upload_root / ".delete-trash" / f"document-{document_id}-{txid}"
                try:
                    trash_dir.mkdir(parents=True, exist_ok=False)
                    storage_path = safe_upload_path(document["storage_path"], upload_root)
                    if not storage_path.is_file():
                        raise OSError(f"document file missing: {storage_path}")
                    trash_path = trash_dir / f"{document_id}-{storage_path.name}"
                    storage_path.replace(trash_path)
                    moved_files.append((trash_path, storage_path))
                except OSError as exc:
                    raise HTTPException(status_code=500, detail="资料文件删除失败") from exc

                conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (document["project_id"],))
                conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))
    except HTTPException:
        restore_deleted_files(moved_files, trash_dir)
        raise
    except Exception as exc:
        restore_deleted_files(moved_files, trash_dir)
        raise HTTPException(status_code=500, detail="资料文件删除失败") from exc

    if trash_dir is not None:
        try:
            shutil.rmtree(trash_dir)
        except OSError:
            logger.exception("failed to clean document delete trash: %s", trash_dir)


def safe_upload_path(raw_path: str, upload_root: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    resolved = path.resolve()
    try:
        resolved.relative_to(upload_root)
    except ValueError as exc:
        raise OSError(f"document file is outside upload dir: {resolved}") from exc
    return resolved


def restore_deleted_files(moved_files: list[tuple[Path, Path]], trash_dir: Path | None) -> None:
    for trash_path, original_path in reversed(moved_files):
        try:
            original_path.parent.mkdir(parents=True, exist_ok=True)
            trash_path.replace(original_path)
        except OSError:
            logger.exception("failed to restore deleted file: %s -> %s", trash_path, original_path)
    if trash_dir is not None:
        shutil.rmtree(trash_dir, ignore_errors=True)


@app.post("/projects/{project_id}/questions")
def create_question(project_id: int, payload: dict[str, Any]) -> dict:
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="题目不能为空")
    document_ids = validate_question_document_scope(project_id, payload.get("document_ids"))
    question_id = search_question(project_id, text, document_ids)
    return get_question(question_id)


def validate_question_document_scope(project_id: int, raw_document_ids: Any) -> list[int] | None:
    with connect() as conn:
        project = conn.execute("SELECT id FROM projects WHERE id = %s", (project_id,)).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        if raw_document_ids is None:
            searchable_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM documents
                WHERE project_id = %s
                  AND status = 'completed'
                  AND searchable = true
                """,
                (project_id,),
            ).fetchone()["count"]
            if searchable_count == 0:
                raise HTTPException(status_code=409, detail="需先上传并处理资料")
            return None

        if not isinstance(raw_document_ids, list):
            raise HTTPException(status_code=400, detail="检索范围包含不可用资料")
        if not raw_document_ids:
            raise HTTPException(status_code=400, detail="检索范围不能为空")

        document_ids: list[int] = []
        for value in raw_document_ids:
            if not isinstance(value, int):
                raise HTTPException(status_code=400, detail="检索范围包含不可用资料")
            if value not in document_ids:
                document_ids.append(value)

        valid_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM documents
            WHERE project_id = %s
              AND id = ANY(%s)
              AND status = 'completed'
              AND searchable = true
            """,
            (project_id, document_ids),
        ).fetchone()["count"]
    if valid_count != len(document_ids):
        raise HTTPException(status_code=400, detail="检索范围包含不可用资料")
    return document_ids


@app.get("/questions/{question_id}")
def get_question(question_id: int) -> dict:
    with connect() as conn:
        question = conn.execute("SELECT * FROM questions WHERE id = %s", (question_id,)).fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="题目不存在")
        matches = conn.execute(
            """
            SELECT
              qm.id,
              qm.question_id,
              qm.document_id,
              d.filename AS document_filename,
              c.id AS chunk_id,
              qm.page_no,
              qm.rank,
              qm.score,
              qm.confidence_level,
              qm.hit_reason,
              qm.source_text,
              qm.context_before,
              qm.context_after,
              d.filename,
              '/documents/' || d.id || '/file#page=' || c.page_no AS pdf_url
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE qm.question_id = %s
              AND qm.source_text IS NOT NULL
              AND length(trim(qm.source_text)) > 0
              AND c.page_no IS NOT NULL
              AND d.filename IS NOT NULL
            ORDER BY qm.rank
            LIMIT 5
            """,
            (question_id,),
        ).fetchall()
        return {"question": question, "matches": [match_response(row) for row in matches]}


@app.get("/questions/{question_id}/matches/{match_id}")
def get_question_match(question_id: int, match_id: int) -> dict:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              qm.id,
              qm.question_id,
              qm.document_id,
              d.filename AS document_filename,
              d.filename,
              c.id AS chunk_id,
              qm.page_no,
              qm.score,
              qm.rank,
              qm.confidence_level,
              qm.hit_reason,
              qm.source_text,
              qm.context_before,
              qm.context_after,
              '/documents/' || d.id || '/file#page=' || qm.page_no AS pdf_url
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            JOIN documents d ON d.id = qm.document_id
            WHERE qm.question_id = %s
              AND qm.id = %s
              AND d.status = 'completed'
              AND d.searchable = true
            """,
            (question_id, match_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="来源已失效")
    return match_response(row)


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: int) -> FileResponse:
    with connect() as conn:
        document = conn.execute("SELECT storage_path, filename FROM documents WHERE id = %s", (document_id,)).fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="资料不存在")
    if not Path(document["storage_path"]).exists():
        raise HTTPException(status_code=404, detail="资料文件不存在")
    return FileResponse(document["storage_path"], media_type="application/pdf", filename=document["filename"])


def project_select_sql(where_clause: str = "") -> str:
    return f"""
            SELECT
              p.id,
              p.workspace_id,
              p.name,
              COUNT(DISTINCT d.id)::int AS document_count,
              COUNT(DISTINCT q.id)::int AS question_count,
              CASE
                WHEN COUNT(DISTINCT d.id) = 0 THEN 'empty'
                WHEN COUNT(DISTINCT d.id) FILTER (WHERE d.status IN ('uploaded', 'processing', 'deleting')) > 0 THEN 'processing'
                WHEN COUNT(DISTINCT d.id) FILTER (WHERE d.status IN ('failed', 'unsupported')) > 0 THEN 'failed'
                ELSE 'ready'
              END AS latest_status,
              p.created_at,
              p.updated_at
            FROM projects p
            LEFT JOIN documents d ON d.project_id = p.id
            LEFT JOIN questions q ON q.project_id = p.id
            {where_clause}
            GROUP BY p.id
            """


def document_select_sql(where_clause: str = "") -> str:
    return f"""
            SELECT
              id,
              project_id,
              filename,
              content_type,
              page_count,
              extractable_page_count,
              chunk_count,
              text_quality,
              searchable,
              status,
              processing_stage,
              failed_stage,
              failure_code,
              failure_reason,
              created_at,
              processed_at,
              updated_at
            FROM documents
            {where_clause}
            """


def document_response(row: dict) -> dict:
    result = dict(row)
    result["text_quality_label"] = TEXT_QUALITY_LABELS[result["text_quality"]]
    return result


def match_response(row: dict) -> dict:
    result = dict(row)
    result["confidence_label"] = CONFIDENCE_LABELS[result["confidence_level"]]
    return result
