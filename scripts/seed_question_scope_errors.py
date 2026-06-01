from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from app.config import settings
from app.db import connect


def main() -> None:
    suffix = time.time_ns()
    project_name = f"题目范围错误项目 {suffix}"
    other_project_name = f"题目范围跨项目 {suffix}"
    repo_root = Path(__file__).resolve().parents[1]
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name, updated_at) VALUES (%s, now()) RETURNING id", (project_name,)).fetchone()
        other_project = conn.execute("INSERT INTO projects (name, updated_at) VALUES (%s, now()) RETURNING id", (other_project_name,)).fetchone()
        searchable = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="scope-searchable.pdf",
            status="completed",
            processing_stage="completed",
            searchable=True,
            chunk_count=1,
            text_quality="good",
        )
        processing = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="scope-processing.pdf",
            status="processing",
            processing_stage="embedding",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        unsearchable = insert_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="scope-unsearchable.pdf",
            status="completed",
            processing_stage="completed",
            searchable=False,
            chunk_count=0,
            text_quality="unsearchable",
        )
        other = insert_document(
            conn,
            other_project["id"],
            repo_root,
            upload_root,
            suffix,
            filename="scope-other.pdf",
            status="completed",
            processing_stage="completed",
            searchable=True,
            chunk_count=1,
            text_quality="good",
        )
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": project_name,
                "other_project_id": other_project["id"],
                "searchable_document_id": searchable["id"],
                "processing_document_id": processing["id"],
                "unsearchable_document_id": unsearchable["id"],
                "other_document_id": other["id"],
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
    status: str,
    processing_stage: str,
    searchable: bool,
    chunk_count: int,
    text_quality: str,
):
    storage_path = upload_root / f"{suffix}-{filename}"
    shutil.copyfile(repo_root / "tests/fixtures/text-layer-material.pdf", storage_path)
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
          %s, %s, 'application/pdf', %s, 1, 1, %s, %s, %s, %s, %s, %s, NULL, NULL,
          '2026-01-01 01:02:03+08', '2026-01-02 03:04:05+08', '2026-03-04 05:06:07+08'
        )
        RETURNING id
        """,
        (project_id, filename, relative_storage_path, chunk_count, text_quality, searchable, status, processing_stage, None),
    ).fetchone()


if __name__ == "__main__":
    main()
