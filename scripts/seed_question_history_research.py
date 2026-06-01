from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from app.config import settings
from app.db import connect, vector_literal


def main() -> None:
    suffix = time.time_ns()
    project_name = f"历史重新检索项目 {suffix}"
    question_text = "history research question"
    repo_root = Path(__file__).resolve().parents[1]
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    storage_path = upload_root / f"{suffix}-history-research.pdf"
    shutil.copyfile(repo_root / "tests/fixtures/text-layer-material.pdf", storage_path)
    relative_storage_path = storage_path.relative_to(repo_root).as_posix()

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name, updated_at) VALUES (%s, now()) RETURNING id", (project_name,)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage, created_at, processed_at, updated_at
            )
            VALUES (
              %s, 'history-research.pdf', 'application/pdf', %s, 1,
              1, 2, 'good', true, 'completed', 'completed',
              '2026-01-01 01:02:03+08', '2026-01-02 03:04:05+08', '2026-03-04 05:06:07+08'
            )
            RETURNING id
            """,
            (project["id"], relative_storage_path),
        ).fetchone()
        page_text = "old history source new history source"
        page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, %s, %s, %s)
            RETURNING id
            """,
            (document["id"], page_text, page_text, len(page_text)),
        ).fetchone()
        old_start = page_text.index("old history source")
        old_chunk = conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char,
              embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, 'old history source', %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-question-history-research')
            RETURNING id
            """,
            (document["id"], page["id"], old_start, old_start + len("old history source"), vector_literal([1.0] + [0.0] * 1023)),
        ).fetchone()
        new_start = page_text.index("new history source")
        conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char,
              embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, 'new history source', %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-question-history-research')
            """,
            (document["id"], page["id"], new_start, new_start + len("new history source"), vector_literal([0.0, 1.0] + [0.0] * 1022)),
        )
        question = conn.execute(
            """
            INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
            VALUES (%s, %s, 'completed', '2001-01-01 00:00:00+00', '2001-01-01 00:00:00+00')
            RETURNING id
            """,
            (project["id"], question_text),
        ).fetchone()
        old_match = conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 1, 0.88, 1, 'strong', 'history fixture', 'old history source', '', ' new history source')
            RETURNING id
            """,
            (question["id"], old_chunk["id"], document["id"]),
        ).fetchone()
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": project_name,
                "question_id": question["id"],
                "question_text": question_text,
                "document_id": document["id"],
                "old_match_id": old_match["id"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
