from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from app.config import settings
from app.db import connect


def main() -> None:
    suffix = time.time_ns()
    project_name = f"无可靠来源项目 {suffix}"
    repo_root = Path(__file__).resolve().parents[1]
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    question_text = "请判断这道题是否能从当前资料中找到可靠出处。"

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name, updated_at) VALUES (%s, now()) RETURNING id", (project_name,)).fetchone()
        searchable = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="no-source-ready.pdf",
            fixture="tests/fixtures/text-layer-material.pdf",
            page_count=1,
            extractable_page_count=1,
            chunk_count=0,
            text_quality="good",
            searchable=True,
            status="completed",
            processing_stage="completed",
            failure_reason=None,
        )
        unavailable = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="no-source-scanned.pdf",
            fixture="tests/fixtures/scanned.pdf",
            page_count=1,
            extractable_page_count=0,
            chunk_count=0,
            text_quality="unsearchable",
            searchable=False,
            status="unsupported",
            processing_stage="failed",
            failure_reason="PDF 无可提取文字层，v0.2.0 不进入 OCR",
        )
        question = conn.execute(
            """
            INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
            VALUES (%s, %s, 'no_reliable_source', now(), now())
            RETURNING id
            """,
            (project["id"], question_text),
        ).fetchone()
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": project_name,
                "question_id": question["id"],
                "question_text": question_text,
                "searchable_document_id": searchable["id"],
                "unavailable_document_id": unavailable["id"],
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
    failure_reason: str | None,
):
    storage_path = upload_root / f"{suffix}-{filename}"
    shutil.copyfile(repo_root / fixture, storage_path)
    relative_storage_path = storage_path.relative_to(repo_root).as_posix()
    failed_stage = "extracting_text" if not searchable else None
    failure_code = "no_text_layer" if not searchable else None
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
