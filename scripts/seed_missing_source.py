from __future__ import annotations

from app.db import connect


def main() -> None:
    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES ('missing-source-seed') RETURNING id").fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (project_id, filename, content_type, storage_path, page_count, status)
            VALUES (%s, 'missing-source.pdf', 'application/pdf', 'uploads/missing-source.pdf', 1, 'completed')
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()
        page = conn.execute(
            "INSERT INTO document_pages (document_id, page_no, raw_text) VALUES (%s, 1, 'seed') RETURNING id",
            (document["id"],),
        ).fetchone()
        zero_vector = "[" + ",".join(["0"] * 1024) + "]"
        chunk = conn.execute(
            """
            INSERT INTO chunks (
              document_id, page_id, page_no, text, embedding, embedding_provider,
              embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, 'seed', %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed')
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
            INSERT INTO question_matches (question_id, chunk_id, score, rank, hit_reason, source_text)
            VALUES (%s, %s, 0.1, 1, 'seed missing source', '')
            """,
            (question["id"], chunk["id"]),
        )
        conn.commit()
    print(question["id"])


if __name__ == "__main__":
    main()
