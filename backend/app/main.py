from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.db import connect
from app.processing import create_uploaded_document, queue_process_document, search_question

app = FastAPI(title="Suton v0.1.0 API")

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
            """
            SELECT
              p.id,
              p.name,
              p.created_at,
              COUNT(DISTINCT d.id)::int AS document_count,
              COUNT(DISTINCT q.id)::int AS question_count,
              COALESCE(
                (SELECT d2.status FROM documents d2 WHERE d2.project_id = p.id ORDER BY d2.created_at DESC LIMIT 1),
                'none'
              ) AS latest_status
            FROM projects p
            LEFT JOIN documents d ON d.project_id = p.id
            LEFT JOIN questions q ON q.project_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        ).fetchall()


@app.post("/projects")
def create_project(payload: dict[str, str]) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    with connect() as conn:
        row = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING *", (name,)).fetchone()
        conn.commit()
        return row


@app.get("/projects/{project_id}")
def get_project(project_id: int) -> dict:
    with connect() as conn:
        project = conn.execute(
            """
            SELECT
              p.id,
              p.name,
              p.created_at,
              COUNT(DISTINCT d.id)::int AS document_count,
              COUNT(DISTINCT q.id)::int AS question_count,
              COALESCE(
                (SELECT d2.status FROM documents d2 WHERE d2.project_id = p.id ORDER BY d2.created_at DESC LIMIT 1),
                'none'
              ) AS latest_status
            FROM projects p
            LEFT JOIN documents d ON d.project_id = p.id
            LEFT JOIN questions q ON q.project_id = p.id
            WHERE p.id = %s
            GROUP BY p.id
            """,
            (project_id,),
        ).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        return project


@app.get("/projects/{project_id}/documents")
def list_documents(project_id: int) -> list[dict]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT id, project_id, filename, content_type, storage_path, page_count, status, failure_reason, created_at
            FROM documents
            WHERE project_id = %s
            ORDER BY created_at DESC
            """,
            (project_id,),
        ).fetchall()


@app.post("/projects/{project_id}/documents")
def upload_document(project_id: int, file: UploadFile = File(...)) -> dict:
    if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="v0.1.0 只支持上传 PDF 文件")
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        project = conn.execute("SELECT id FROM projects WHERE id = %s", (project_id,)).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    safe_name = Path(file.filename).name
    storage_path = upload_root / f"project-{project_id}-{safe_name}"
    with storage_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    document_id = create_uploaded_document(project_id, safe_name, "application/pdf", str(storage_path))
    queue_process_document(document_id)
    return {"id": document_id, "filename": safe_name, "status": "uploaded"}


@app.post("/projects/{project_id}/questions")
def create_question(project_id: int, payload: dict[str, str]) -> dict:
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="题目不能为空")
    with connect() as conn:
        completed_count = conn.execute(
            "SELECT COUNT(*) AS count FROM documents WHERE project_id = %s AND status = 'completed'",
            (project_id,),
        ).fetchone()["count"]
    if completed_count == 0:
        raise HTTPException(status_code=409, detail="需先上传并处理资料")
    question_id = search_question(project_id, text)
    return get_question(question_id)


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
              qm.rank,
              qm.score,
              qm.hit_reason,
              qm.source_text,
              c.page_no,
              d.filename,
              d.id AS document_id,
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
        return {"question": question, "matches": matches}


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: int) -> FileResponse:
    with connect() as conn:
        document = conn.execute("SELECT storage_path, filename FROM documents WHERE id = %s", (document_id,)).fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="资料不存在")
    return FileResponse(document["storage_path"], media_type="application/pdf", filename=document["filename"])
