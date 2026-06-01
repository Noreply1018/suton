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
    storage_path = upload_root / f"{suffix}-source-reader.pdf"
    shutil.copyfile(repo_root / "tests/fixtures/text-layer-material.pdf", storage_path)
    relative_storage_path = storage_path.relative_to(repo_root).as_posix()
    zero_vector = "[" + ",".join(["0"] * 1024) + "]"
    page_text = "source reader before source reader hit source reader after"
    source_text = "source reader hit"
    source_start = page_text.index(source_text)
    source_end = source_start + len(source_text)

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"来源阅读项目 {suffix}",)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage, processed_at
            )
            VALUES (%s, 'source-reader.pdf', 'application/pdf', %s, 2, 2, 1, 'good', true, 'completed', 'completed', now())
            RETURNING id
            """,
            (project["id"], relative_storage_path),
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
              document_id, page_id, page_no, text, page_start_char, page_end_char, embedding,
              embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-source-reader')
            RETURNING id
            """,
            (document["id"], page["id"], source_text, source_start, source_end, zero_vector),
        ).fetchone()
        question = conn.execute(
            """
            INSERT INTO questions (project_id, text, status, last_search_at)
            VALUES (%s, 'source reader question', 'completed', now())
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()
        match = conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 1, 0.91, 1, 'strong', 'seed source reader fixture', %s, 'source reader before ', ' source reader after')
            RETURNING id
            """,
            (question["id"], chunk["id"], document["id"], source_text),
        ).fetchone()
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": f"来源阅读项目 {suffix}",
                "question_id": question["id"],
                "document_id": document["id"],
                "match_id": match["id"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
