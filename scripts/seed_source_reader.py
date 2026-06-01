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
    first_page_text = "source reader before source reader hit source reader after"
    first_source_text = "source reader hit"
    first_source_start = first_page_text.index(first_source_text)
    first_source_end = first_source_start + len(first_source_text)
    second_page_text = "switch reader before second source hit switch reader after"
    second_source_text = "second source hit"
    second_source_start = second_page_text.index(second_source_text)
    second_source_end = second_source_start + len(second_source_text)

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"来源阅读项目 {suffix}",)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage, processed_at
            )
            VALUES (%s, 'source-reader.pdf', 'application/pdf', %s, 2, 2, 2, 'good', true, 'completed', 'completed', now())
            RETURNING id
            """,
            (project["id"], relative_storage_path),
        ).fetchone()
        first_page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, %s, %s, %s)
            RETURNING id
            """,
            (document["id"], first_page_text, first_page_text, len(first_page_text)),
        ).fetchone()
        second_page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 2, %s, %s, %s)
            RETURNING id
            """,
            (document["id"], second_page_text, second_page_text, len(second_page_text)),
        ).fetchone()
        first_chunk = conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char, embedding,
              embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-source-reader')
            RETURNING id
            """,
            (document["id"], first_page["id"], first_source_text, first_source_start, first_source_end, zero_vector),
        ).fetchone()
        second_chunk = conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char, embedding,
              embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 2, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-source-reader')
            RETURNING id
            """,
            (document["id"], second_page["id"], second_source_text, second_source_start, second_source_end, zero_vector),
        ).fetchone()
        question = conn.execute(
            """
            INSERT INTO questions (project_id, text, status, last_search_at)
            VALUES (%s, 'source reader question', 'completed', now())
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()
        first_match = conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 1, 0.91, 1, 'strong', 'seed source reader fixture', %s, 'source reader before ', ' source reader after')
            RETURNING id
            """,
            (question["id"], first_chunk["id"], document["id"], first_source_text),
        ).fetchone()
        second_match = conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 2, 0.73, 2, 'reference', 'seed source switch fixture', %s, 'switch reader before ', ' switch reader after')
            RETURNING id
            """,
            (question["id"], second_chunk["id"], document["id"], second_source_text),
        ).fetchone()
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": f"来源阅读项目 {suffix}",
                "question_id": question["id"],
                "document_id": document["id"],
                "match_id": first_match["id"],
                "second_match_id": second_match["id"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
