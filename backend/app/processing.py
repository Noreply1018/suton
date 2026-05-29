from __future__ import annotations

import re
from pathlib import Path

import fitz
import psycopg

from app.config import settings
from app.db import connect, vector_literal
from app.embedding import embed_texts


MAX_CHUNK_CHARS = 2000
MIN_MATCH_SCORE = 0.40


def split_page_text(text: str) -> list[str]:
    clean = re.sub(r"[ \t]+", " ", text).strip()
    if not clean:
        return []
    if len(clean) <= MAX_CHUNK_CHARS:
        return [clean]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", clean) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        parts = [paragraph]
        if len(paragraph) > MAX_CHUNK_CHARS:
            parts = [paragraph[i : i + MAX_CHUNK_CHARS] for i in range(0, len(paragraph), MAX_CHUNK_CHARS)]
        for part in parts:
            if not current:
                current = part
            elif len(current) + 2 + len(part) <= MAX_CHUNK_CHARS:
                current = f"{current}\n\n{part}"
            else:
                chunks.append(current)
                current = part
    if current:
        chunks.append(current)
    return chunks


def process_document(document_id: int) -> None:
    with connect() as conn:
        document = conn.execute("SELECT * FROM documents WHERE id = %s", (document_id,)).fetchone()
        if not document:
            raise ValueError(f"document not found: {document_id}")
        conn.execute("UPDATE documents SET status = 'processing', failure_reason = NULL WHERE id = %s", (document_id,))
        conn.commit()

    try:
        pages_and_chunks = extract_pages_and_chunks(Path(document["storage_path"]))
        if not pages_and_chunks:
            mark_document_failed(document_id, "PDF 无可提取文字层，v0.1.0 不进入 OCR", status="unsupported")
            return
        with connect() as conn:
            with conn.transaction():
                conn.execute("DELETE FROM document_pages WHERE document_id = %s", (document_id,))
                page_count = len(pages_and_chunks)
                all_chunks: list[tuple[int, str]] = []
                page_ids: dict[int, int] = {}
                for page_no, raw_text, chunks in pages_and_chunks:
                    page = conn.execute(
                        """
                        INSERT INTO document_pages (document_id, page_no, raw_text)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (document_id, page_no, raw_text),
                    ).fetchone()
                    page_ids[page_no] = page["id"]
                    for chunk in chunks:
                        all_chunks.append((page_no, chunk))
                embeddings = embed_texts([chunk for _, chunk in all_chunks])
                for (page_no, chunk), embedding in zip(all_chunks, embeddings, strict=True):
                    conn.execute(
                        """
                        INSERT INTO chunks (
                          document_id, page_id, page_no, text, section_title, embedding,
                          embedding_provider, embedding_model, embedding_dimension, embedding_call
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            page_ids[page_no],
                            page_no,
                            chunk,
                            None,
                            vector_literal(embedding),
                            settings.embedding_provider,
                            settings.embedding_model,
                            settings.embedding_dimension,
                            "OpenAI Python SDK /embeddings encoding_format=float",
                        ),
                    )
                conn.execute(
                    """
                    UPDATE documents
                    SET status = 'completed', page_count = %s, processed_at = now(), failure_reason = NULL
                    WHERE id = %s
                    """,
                    (page_count, document_id),
                )
    except Exception as exc:  # noqa: BLE001
        mark_document_failed(document_id, str(exc), status="failed")
        raise


def extract_pages_and_chunks(path: Path) -> list[tuple[int, str, list[str]]]:
    result: list[tuple[int, str, list[str]]] = []
    with fitz.open(path) as pdf:
        for index, page in enumerate(pdf, start=1):
            raw_text = page.get_text("text").strip()
            chunks = split_page_text(raw_text)
            if raw_text and chunks:
                result.append((index, raw_text, chunks))
    return result


def mark_document_failed(document_id: int, reason: str, status: str = "failed") -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE documents
            SET status = %s, failure_reason = %s, processed_at = now()
            WHERE id = %s
            """,
            (status, reason[:1000], document_id),
        )
        conn.commit()


def create_uploaded_document(project_id: int, filename: str, content_type: str, storage_path: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO documents (project_id, filename, content_type, storage_path, status)
            VALUES (%s, %s, %s, %s, 'uploaded')
            RETURNING id
            """,
            (project_id, filename, content_type, storage_path),
        ).fetchone()
        conn.commit()
        return row["id"]


def search_question(project_id: int, text: str) -> int:
    query_embedding = embed_texts([text])[0]
    with connect() as conn:
        question = conn.execute(
            """
            INSERT INTO questions (project_id, text, status)
            VALUES (%s, %s, 'searching')
            RETURNING id
            """,
            (project_id, text),
        ).fetchone()
        question_id = question["id"]
        rows = conn.execute(
            """
            SELECT
              c.id AS chunk_id,
              c.text AS source_text,
              1 - (c.embedding <=> %s::vector) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.project_id = %s
              AND d.status = 'completed'
              AND c.text IS NOT NULL
              AND c.page_no IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT 5
            """,
            (vector_literal(query_embedding), project_id, vector_literal(query_embedding)),
        ).fetchall()
        rows = [row for row in rows if float(row["score"]) >= MIN_MATCH_SCORE]
        for rank, row in enumerate(rows, start=1):
            snippet = row["source_text"][:700]
            conn.execute(
                """
                INSERT INTO question_matches (question_id, chunk_id, score, rank, hit_reason, source_text)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    question_id,
                    row["chunk_id"],
                    float(row["score"]),
                    rank,
                    "pgvector cosine similarity against DashScope text-embedding-v4 dense embedding",
                    snippet,
                ),
            )
        conn.execute(
            "UPDATE questions SET status = %s WHERE id = %s",
            ("completed" if rows else "no_results", question_id),
        )
        conn.commit()
        return question_id


def queue_process_document(document_id: int) -> None:
    from redis import Redis
    from rq import Queue

    queue = Queue("suton", connection=Redis.from_url(settings.redis_url))
    queue.enqueue("app.processing.process_document", document_id)
