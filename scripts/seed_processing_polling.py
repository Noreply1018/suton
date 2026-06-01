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
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"处理中轮询项目 {suffix}",)).fetchone()
        document_ids = [
            insert_processing_document(conn, project["id"], repo_root, upload_root, suffix, index)
            for index in range(1, 4)
        ]
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": f"处理中轮询项目 {suffix}",
                "document_ids": document_ids,
            },
            ensure_ascii=False,
        )
    )


def insert_processing_document(conn, project_id: int, repo_root: Path, upload_root: Path, suffix: int, index: int) -> int:
    filename = f"processing-polling-{index}.pdf"
    storage_path = upload_root / f"{suffix}-{filename}"
    shutil.copyfile(repo_root / "tests/fixtures/text-layer-material.pdf", storage_path)
    row = conn.execute(
        """
        INSERT INTO documents (
          project_id, filename, content_type, storage_path, page_count,
          extractable_page_count, chunk_count, text_quality, searchable,
          status, processing_stage, failed_stage, failure_code, failure_reason,
          created_at, processed_at, updated_at
        )
        VALUES (
          %s, %s, 'application/pdf', %s, 2, 2, 0, 'good', false,
          'processing', 'embedding', NULL, NULL, NULL,
          '2026-01-01 01:02:03+08', NULL, '2026-03-04 05:06:07+08'
        )
        RETURNING id
        """,
        (project_id, filename, storage_path.relative_to(repo_root).as_posix()),
    ).fetchone()
    return row["id"]


if __name__ == "__main__":
    main()
