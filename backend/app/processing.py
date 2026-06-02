from __future__ import annotations

import re
from pathlib import Path

import fitz
from openai import OpenAIError
import psycopg

from app.config import settings
from app.db import connect, vector_literal
from app.embedding import EmbeddingConfigurationError, embed_texts


MAX_CHUNK_CHARS = 2000
MIN_MATCH_SCORE = 0.40
CONTEXT_CHARS = 300
DOCUMENT_FAILURE_REASONS = {
    "invalid_pdf": "PDF 文件损坏，无法读取",
    "unsupported_file_type": "文件类型不受支持",
    "no_text_layer": "PDF 无可提取文字层，v0.2.0 不进入 OCR",
    "extract_text_failed": "提取文字失败",
    "chunking_failed": "切块失败",
    "embedding_failed": "生成 embedding 失败",
    "indexing_failed": "建立索引失败",
    "storage_missing": "资料文件不存在",
    "delete_file_failed": "资料文件删除失败",
    "unknown_processing_error": "资料处理失败",
}
QUESTION_FAILURE_REASONS = {
    "embedding_failed": "题目向量生成失败",
    "source_context_failed": "来源上下文生成失败",
    "search_failed": "题目检索失败",
}


def confidence_level_for_score(score: float) -> str:
    if score >= 0.72:
        return "strong"
    if score >= 0.55:
        return "reference"
    return "low"


def text_quality_for_counts(extractable_page_count: int, page_count: int) -> str:
    if page_count <= 0 or extractable_page_count <= 0:
        return "unsearchable"
    ratio = extractable_page_count / page_count
    if ratio >= 0.90:
        return "good"
    if ratio >= 0.50:
        return "fair"
    return "poor"


def document_searchable_for_fields(status: str, chunk_count: int, text_quality: str) -> bool:
    return status == "completed" and chunk_count > 0 and text_quality != "unsearchable"


def normalize_page_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def split_page_text(text: str) -> list[str]:
    return [chunk for chunk, _, _ in split_page_text_with_offsets(text)]


def split_page_text_with_offsets(text: str) -> list[tuple[str, int, int]]:
    clean = normalize_page_text(text)
    if not clean:
        return []
    if len(clean) <= MAX_CHUNK_CHARS:
        return [(clean, 0, len(clean))]
    paragraph_spans = [(match.start(), match.end()) for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", clean, flags=re.DOTALL)]
    chunks: list[tuple[str, int, int]] = []
    current_start: int | None = None
    current_end: int | None = None
    for paragraph_start, paragraph_end in paragraph_spans:
        parts = [(paragraph_start, paragraph_end)]
        if paragraph_end - paragraph_start > MAX_CHUNK_CHARS:
            parts = [
                (start, min(start + MAX_CHUNK_CHARS, paragraph_end))
                for start in range(paragraph_start, paragraph_end, MAX_CHUNK_CHARS)
            ]
        for part_start, part_end in parts:
            if current_start is None or current_end is None:
                current_start = part_start
                current_end = part_end
            elif part_end - current_start <= MAX_CHUNK_CHARS:
                current_end = part_end
            else:
                chunks.append((clean[current_start:current_end], current_start, current_end))
                current_start = part_start
                current_end = part_end
    if current_start is not None and current_end is not None:
        chunks.append((clean[current_start:current_end], current_start, current_end))
    return chunks


def process_document(document_id: int) -> None:
    with connect() as conn:
        document = conn.execute("SELECT * FROM documents WHERE id = %s", (document_id,)).fetchone()
        if not document:
            raise ValueError(f"document not found: {document_id}")
        conn.execute(
            """
            UPDATE documents
            SET status = 'processing', processing_stage = 'extracting_text', failure_code = NULL,
                failure_reason = NULL, failed_stage = NULL, updated_at = now()
            WHERE id = %s
            """,
            (document_id,),
        )
        conn.commit()

    try:
        total_page_count, pages_and_chunks = extract_pages_and_chunks(Path(document["storage_path"]))
        if not pages_and_chunks:
            with connect() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET page_count = %s, extractable_page_count = 0, chunk_count = 0,
                        text_quality = 'unsearchable', searchable = false, updated_at = now()
                    WHERE id = %s
                    """,
                    (total_page_count, document_id),
                )
                conn.commit()
            mark_document_failed(document_id, DOCUMENT_FAILURE_REASONS["no_text_layer"], status="unsupported")
            return
        with connect() as conn:
            with conn.transaction():
                conn.execute("DELETE FROM document_pages WHERE document_id = %s", (document_id,))
                all_chunks: list[tuple[int, str, int, int]] = []
                page_ids: dict[int, int] = {}
                normalized_pages: dict[int, str] = {}
                for page_no, raw_text, chunks in pages_and_chunks:
                    normalized_text = normalize_page_text(raw_text)
                    page = conn.execute(
                        """
                        INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (document_id, page_no, raw_text, normalized_text, len(normalized_text)),
                    ).fetchone()
                    page_ids[page_no] = page["id"]
                    normalized_pages[page_no] = normalized_text
                    for chunk, start, end in chunks:
                        all_chunks.append((page_no, chunk, start, end))
                conn.execute(
                    """
                    UPDATE documents
                    SET processing_stage = 'embedding', page_count = %s,
                        extractable_page_count = %s, chunk_count = %s,
                        text_quality = %s, searchable = false, updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        total_page_count,
                        len(normalized_pages),
                        len(all_chunks),
                        text_quality_for_counts(len(normalized_pages), total_page_count),
                        document_id,
                    ),
                )
        embeddings = embed_texts([chunk for _, chunk, _, _ in all_chunks])
        with connect() as conn:
            conn.execute("UPDATE documents SET processing_stage = 'indexing', updated_at = now() WHERE id = %s", (document_id,))
            conn.commit()
        with connect() as conn:
            with conn.transaction():
                for (page_no, chunk, start, end), embedding in zip(all_chunks, embeddings, strict=True):
                    conn.execute(
                        """
                        INSERT INTO chunks (
                          document_id, page_id, page_no, text, page_start_char, page_end_char, section_title, embedding,
                          embedding_provider, embedding_model, embedding_dimension, embedding_call
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            page_ids[page_no],
                            page_no,
                            chunk,
                            start,
                            end,
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
                    SET status = 'completed', processing_stage = 'completed', page_count = %s,
                        extractable_page_count = %s, chunk_count = %s,
                        text_quality = %s, searchable = %s, processed_at = now(),
                        failure_code = NULL, failure_reason = NULL, failed_stage = NULL, updated_at = now()
                    WHERE id = %s
                    """,
                    (
                        total_page_count,
                        len(normalized_pages),
                        len(all_chunks),
                        text_quality_for_counts(len(normalized_pages), total_page_count),
                        document_searchable_for_fields(
                            "completed",
                            len(all_chunks),
                            text_quality_for_counts(len(normalized_pages), total_page_count),
                        ),
                        document_id,
                    ),
                )
    except Exception as exc:  # noqa: BLE001
        failure_code = "invalid_pdf" if isinstance(exc, fitz.FileDataError) else None
        mark_document_failed(document_id, str(exc), status="failed", failure_code=failure_code)
        raise


def extract_pages_and_chunks(path: Path) -> tuple[int, list[tuple[int, str, list[tuple[str, int, int]]]]]:
    result: list[tuple[int, str, list[tuple[str, int, int]]]] = []
    with fitz.open(path) as pdf:
        page_count = len(pdf)
        for index, page in enumerate(pdf, start=1):
            raw_text = page.get_text("text").strip()
            chunks = split_page_text_with_offsets(raw_text)
            if raw_text and chunks:
                result.append((index, raw_text, chunks))
    return page_count, result


def mark_document_failed(document_id: int, reason: str, status: str = "failed", failure_code: str | None = None) -> None:
    with connect() as conn:
        document = conn.execute("SELECT processing_stage FROM documents WHERE id = %s", (document_id,)).fetchone()
        failed_stage = document["processing_stage"] if document else "uploaded"
        if status == "unsupported":
            failure_code = "no_text_layer"
        elif failure_code is None:
            failure_code = {
                "extracting_text": "extract_text_failed",
                "chunking": "chunking_failed",
                "embedding": "embedding_failed",
                "indexing": "indexing_failed",
            }.get(failed_stage, "unknown_processing_error")
        fixed_reason = DOCUMENT_FAILURE_REASONS[failure_code]
        conn.execute(
            """
            UPDATE documents
            SET status = %s, processing_stage = 'failed', failed_stage = COALESCE(NULLIF(processing_stage, 'failed'), 'uploaded'),
                failure_code = %s, failure_reason = %s, searchable = false, processed_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (status, failure_code, fixed_reason if reason else fixed_reason, document_id),
        )
        conn.commit()


def create_uploaded_document(project_id: int, filename: str, content_type: str, storage_path: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO documents (project_id, filename, content_type, storage_path, status, processing_stage)
            VALUES (%s, %s, %s, %s, 'uploaded', 'uploaded')
            RETURNING id
            """,
            (project_id, filename, content_type, storage_path),
        ).fetchone()
        conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project_id,))
        conn.commit()
        return row["id"]


def reset_document_for_reprocess(document_id: int) -> None:
    with connect() as conn:
        with conn.transaction():
            document = conn.execute(
                "SELECT id, project_id FROM documents WHERE id = %s FOR UPDATE",
                (document_id,),
            ).fetchone()
            if not document:
                raise ValueError(f"document not found: {document_id}")
            conn.execute("DELETE FROM question_matches WHERE document_id = %s", (document_id,))
            conn.execute("DELETE FROM document_pages WHERE document_id = %s", (document_id,))
            conn.execute(
                """
                UPDATE documents
                SET status = 'uploaded', processing_stage = 'uploaded',
                    failed_stage = NULL, failure_code = NULL, failure_reason = NULL,
                    searchable = false, updated_at = now()
                WHERE id = %s
                """,
                (document_id,),
            )
            conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (document["project_id"],))


def search_question(project_id: int, text: str, document_ids: list[int] | None = None) -> int:
    try:
        query_embedding = embed_texts([text])[0]
    except (EmbeddingConfigurationError, OpenAIError):
        return create_failed_question(project_id, text, "embedding_failed")
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
        write_question_search_results(conn, question_id, project_id, query_embedding, document_ids)
        conn.commit()
        return question_id


def create_failed_question(project_id: int, text: str, failure_code: str) -> int:
    with connect() as conn:
        question = conn.execute(
            """
            INSERT INTO questions (
              project_id, text, status, failure_code, failure_reason,
              last_search_at, updated_at
            )
            VALUES (%s, %s, 'failed', %s, %s, now(), now())
            RETURNING id
            """,
            (project_id, text, failure_code, QUESTION_FAILURE_REASONS[failure_code]),
        ).fetchone()
        conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project_id,))
        conn.commit()
        return question["id"]


def research_question(question_id: int, document_ids: list[int] | None = None) -> int:
    with connect() as conn:
        question = conn.execute("SELECT project_id, text FROM questions WHERE id = %s", (question_id,)).fetchone()
    if not question:
        raise ValueError(f"question not found: {question_id}")
    try:
        query_embedding = embed_texts([question["text"]])[0]
    except (EmbeddingConfigurationError, OpenAIError):
        mark_question_failed(question_id, question["project_id"], "embedding_failed")
        return question_id
    return research_question_with_embedding(question_id, document_ids, query_embedding)


def mark_question_failed(question_id: int, project_id: int, failure_code: str) -> None:
    with connect() as conn:
        with conn.transaction():
            conn.execute("DELETE FROM question_matches WHERE question_id = %s", (question_id,))
            conn.execute(
                """
                UPDATE questions
                SET status = 'failed', failure_code = %s, failure_reason = %s,
                    last_search_at = now(), updated_at = now()
                WHERE id = %s
                """,
                (failure_code, QUESTION_FAILURE_REASONS[failure_code], question_id),
            )
            conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project_id,))


def research_question_with_embedding(question_id: int, document_ids: list[int] | None, query_embedding: list[float]) -> int:
    with connect() as conn:
        question = conn.execute("SELECT project_id FROM questions WHERE id = %s", (question_id,)).fetchone()
        if not question:
            raise ValueError(f"question not found: {question_id}")
        with conn.transaction():
            locked = conn.execute("SELECT id FROM questions WHERE id = %s FOR UPDATE", (question_id,)).fetchone()
            if not locked:
                raise ValueError(f"question not found: {question_id}")
            conn.execute("DELETE FROM question_matches WHERE question_id = %s", (question_id,))
            conn.execute(
                """
                UPDATE questions
                SET status = 'searching', failure_code = NULL, failure_reason = NULL,
                    updated_at = now()
                WHERE id = %s
                """,
                (question_id,),
            )
            write_question_search_results(conn, question_id, question["project_id"], query_embedding, document_ids)
    return question_id


def write_question_search_results(conn, question_id: int, project_id: int, query_embedding: list[float], document_ids: list[int] | None) -> None:
    scope_filter = ""
    params: list[object] = [vector_literal(query_embedding), project_id]
    if document_ids is not None:
        scope_filter = "AND d.id = ANY(%s)"
        params.append(document_ids)
    params.append(vector_literal(query_embedding))
    rows = conn.execute(
        f"""
        SELECT
          c.id AS chunk_id,
          c.document_id,
          c.page_no,
          c.text AS source_text,
          c.page_start_char,
          c.page_end_char,
          p.normalized_text,
          1 - (c.embedding <=> %s::vector) AS score
        FROM chunks c
        JOIN document_pages p ON p.id = c.page_id
        JOIN documents d ON d.id = c.document_id
        WHERE d.project_id = %s
          AND d.status = 'completed'
          AND d.searchable = true
          {scope_filter}
          AND c.text IS NOT NULL
          AND c.page_no IS NOT NULL
        ORDER BY c.embedding <=> %s::vector
        LIMIT 20
        """,
        params,
    ).fetchall()
    rows = [row for row in rows if float(row["score"]) >= MIN_MATCH_SCORE]
    for row in rows:
        normalized_text = row["normalized_text"]
        source_text = row["source_text"].strip()
        start = int(row["page_start_char"])
        end = int(row["page_end_char"])
        if start < 0 or end < start or end > len(normalized_text) or normalized_text[start:end] != source_text:
            conn.execute(
                """
                UPDATE questions
                SET status = 'failed', failure_code = 'source_context_failed',
                    failure_reason = '来源上下文生成失败',
                    last_search_at = now(), updated_at = now()
                WHERE id = %s
                """,
                (question_id,),
            )
            conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project_id,))
            return
    for rank, row in enumerate(rows, start=1):
        score = float(row["score"])
        confidence_level = confidence_level_for_score(score)
        source_text = row["source_text"].strip()
        normalized_text = row["normalized_text"]
        start = int(row["page_start_char"])
        end = int(row["page_end_char"])
        context_before = normalized_text[max(0, start - CONTEXT_CHARS) : start]
        context_after = normalized_text[end : end + CONTEXT_CHARS]
        conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                question_id,
                row["chunk_id"],
                row["document_id"],
                row["page_no"],
                score,
                rank,
                confidence_level,
                "pgvector cosine similarity against DashScope text-embedding-v4 dense embedding",
                source_text,
                context_before,
                context_after,
            ),
        )
    conn.execute(
        "UPDATE questions SET status = %s, failure_code = NULL, failure_reason = NULL, last_search_at = now(), updated_at = now() WHERE id = %s",
        ("completed" if rows else "no_reliable_source", question_id),
    )
    conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project_id,))


def queue_process_document(document_id: int) -> None:
    from redis import Redis
    from rq import Queue

    queue = Queue("suton", connection=Redis.from_url(settings.redis_url))
    queue.enqueue("app.processing.process_document", document_id)
