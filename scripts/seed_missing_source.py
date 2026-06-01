from __future__ import annotations

import time

from app.db import connect


def main() -> None:
    with connect() as conn:
        project_name = f"missing-source-seed-{time.time_ns()}"
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (project_name,)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable, status, processing_stage
            )
            VALUES (%s, 'missing-source.pdf', 'application/pdf', 'uploads/missing-source.pdf', 1, 1, 1, 'good', true, 'completed', 'completed')
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()
        page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, 'seed', 'seed', 4)
            RETURNING id
            """,
            (document["id"],),
        ).fetchone()
        zero_vector = "[" + ",".join(["0"] * 1024) + "]"
        chunk = conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, page_start_char, page_end_char, embedding, embedding_provider,
              embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, 'seed', 0, 4, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed')
            RETURNING id
            """,
            (document["id"], page["id"], zero_vector),
        ).fetchone()
        question = conn.execute(
            "INSERT INTO questions (project_id, text, status) VALUES (%s, 'seed', 'completed') RETURNING id",
            (project["id"],),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 1, 0.1, 1, 'low', 'seed missing source', '', '', '')
            """,
            (question["id"], chunk["id"], document["id"]),
        )
        conn.commit()
    print(question["id"])


if __name__ == "__main__":
    main()
