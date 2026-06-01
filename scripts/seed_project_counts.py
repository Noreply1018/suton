from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from app.config import settings
from app.db import connect


def main() -> None:
    suffix = time.time_ns()
    project_name = f"含资料题目项目 {suffix}"
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    storage_path = upload_root / f"e2e-project-delete-{suffix}.pdf"
    shutil.copyfile(Path("tests/fixtures/text-layer-material.pdf"), storage_path)
    relative_storage_path = storage_path.relative_to(Path.cwd()).as_posix()
    zero_vector = "[" + ",".join(["0"] * 1024) + "]"

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (project_name,)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable, status, processing_stage
            )
            VALUES (%s, 'e2e-project-delete.pdf', 'application/pdf', %s, 1, 1, 1, 'good', true, 'completed', 'completed')
            RETURNING id
            """,
            (project["id"], relative_storage_path),
        ).fetchone()
        page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, 'seed project delete', 'seed project delete', 19)
            RETURNING id
            """,
            (document["id"],),
        ).fetchone()
        chunk = conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char, embedding, embedding_provider,
              embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, 'seed project delete', 0, 19, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed')
            RETURNING id
            """,
            (document["id"], page["id"], zero_vector),
        ).fetchone()
        question = conn.execute(
            "INSERT INTO questions (project_id, text, status) VALUES (%s, 'seed project question', 'completed') RETURNING id",
            (project["id"],),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 1, 0.8, 1, 'strong', 'seed project delete', 'seed project delete', '', '')
            """,
            (question["id"], chunk["id"], document["id"]),
        )
        conn.commit()

    print(json.dumps({"id": project["id"], "name": project_name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
