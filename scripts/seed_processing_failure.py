from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from app.config import settings
from app.db import connect


def main() -> None:
    suffix = time.time_ns()
    repo_root = Path(__file__).resolve().parents[1]
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"处理失败项目 {suffix}",)).fetchone()
        reprocess_document = insert_failed_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            "processing-failed-reprocess.pdf",
        )
        delete_document = insert_failed_document(
            conn,
            project["id"],
            repo_root,
            upload_root,
            suffix,
            "processing-failed-delete.pdf",
        )
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": f"处理失败项目 {suffix}",
                "reprocess_document_id": reprocess_document["id"],
                "delete_document_id": delete_document["id"],
            },
            ensure_ascii=False,
        )
    )


def insert_failed_document(conn, project_id: int, repo_root: Path, upload_root: Path, suffix: int, filename: str):
    storage_path = upload_root / f"{suffix}-{filename}"
    shutil.copyfile(repo_root / "tests/fixtures/broken.pdf", storage_path)
    return conn.execute(
        """
        INSERT INTO documents (
          project_id, filename, content_type, storage_path, page_count,
          extractable_page_count, chunk_count, text_quality, searchable,
          status, processing_stage, failed_stage, failure_code, failure_reason,
          created_at, processed_at, updated_at
        )
        VALUES (
          %s, %s, 'application/pdf', %s, 0, 0, 0, 'unsearchable', false,
          'failed', 'failed', 'extracting_text', 'invalid_pdf', 'PDF 文件损坏，无法读取',
          '2026-01-01 01:02:03+08', '2026-01-02 03:04:05+08', '2026-03-04 05:06:07+08'
        )
        RETURNING id
        """,
        (project_id, filename, storage_path.relative_to(repo_root).as_posix()),
    ).fetchone()


if __name__ == "__main__":
    main()
