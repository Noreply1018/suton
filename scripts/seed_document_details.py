from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from app.config import settings
from app.db import connect


def main() -> None:
    suffix = time.time_ns()
    project_name = f"资料详情项目 {suffix}"
    repo_root = Path(__file__).resolve().parents[1]
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    zero_vector = "[" + ",".join(["0"] * 1024) + "]"

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (project_name,)).fetchone()
        completed = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="detail-completed.pdf",
            fixture="tests/fixtures/text-layer-material.pdf",
            page_count=2,
            extractable_page_count=2,
            chunk_count=1,
            text_quality="good",
            searchable=True,
            status="completed",
            processing_stage="completed",
        )
        completed_page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, 'detail completed source', 'detail completed source', 23)
            RETURNING id
            """,
            (completed["id"],),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char, embedding,
              embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, 'detail completed source', 0, 23, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-document-details')
            """,
            (completed["id"], completed_page["id"], zero_vector),
        )
        failed = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="detail-failed.pdf",
            fixture="tests/fixtures/broken.pdf",
            page_count=0,
            extractable_page_count=0,
            chunk_count=0,
            text_quality="unsearchable",
            searchable=False,
            status="failed",
            processing_stage="failed",
            failed_stage="extracting_text",
            failure_code="invalid_pdf",
            failure_reason="PDF 文件损坏，无法读取",
        )
        unsupported = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="detail-scanned.pdf",
            fixture="tests/fixtures/scanned.pdf",
            page_count=1,
            extractable_page_count=0,
            chunk_count=0,
            text_quality="unsearchable",
            searchable=False,
            status="unsupported",
            processing_stage="failed",
            failed_stage="extracting_text",
            failure_code="no_text_layer",
            failure_reason="PDF 无可提取文字层，v0.2.0 不进入 OCR",
        )
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": project_name,
                "completed_id": completed["id"],
                "failed_id": failed["id"],
                "unsupported_id": unsupported["id"],
            },
            ensure_ascii=False,
        )
    )


def insert_document(
    conn,
    project_id: int,
    repo_root: Path,
    upload_root: Path,
    suffix: int,
    *,
    filename: str,
    fixture: str,
    page_count: int,
    extractable_page_count: int,
    chunk_count: int,
    text_quality: str,
    searchable: bool,
    status: str,
    processing_stage: str,
    failed_stage: str | None = None,
    failure_code: str | None = None,
    failure_reason: str | None = None,
):
    storage_path = upload_root / f"{suffix}-{filename}"
    shutil.copyfile(repo_root / fixture, storage_path)
    relative_storage_path = storage_path.relative_to(repo_root).as_posix()
    return conn.execute(
        """
        INSERT INTO documents (
          project_id, filename, content_type, storage_path, page_count,
          extractable_page_count, chunk_count, text_quality, searchable,
          status, processing_stage, failed_stage, failure_code, failure_reason,
          created_at, processed_at, updated_at
        )
        VALUES (
          %s, %s, 'application/pdf', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          '2026-01-01 01:02:03+08', '2026-01-02 03:04:05+08', '2026-03-04 05:06:07+08'
        )
        RETURNING id
        """,
        (
            project_id,
            filename,
            relative_storage_path,
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
        ),
    ).fetchone()


if __name__ == "__main__":
    main()
