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
    zero_vector = "[" + ",".join(["0"] * 1024) + "]"

    with connect() as conn:
        project_ids: list[int] = []
        for index in range(20):
            project = conn.execute(
                """
                INSERT INTO projects (name, updated_at)
                VALUES (%s, now() - (%s || ' minutes')::interval)
                RETURNING id
                """,
                (f"长列表项目 {suffix}-{index + 1:02d}", 30 - index),
            ).fetchone()
            project_ids.append(project["id"])

        active_project_id = project_ids[-1]
        documents = []
        for index in range(20):
            storage_path = upload_root / f"{suffix}-long-list-{index + 1:02d}.pdf"
            shutil.copyfile(repo_root / "tests/fixtures/text-layer-material.pdf", storage_path)
            relative_storage_path = storage_path.relative_to(repo_root).as_posix()
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage, processed_at, updated_at
                )
                VALUES (%s, %s, 'application/pdf', %s, 1, 1, %s, 'good', true, 'completed', 'completed', now(), now())
                RETURNING id
                """,
                (active_project_id, f"long-list-material-{index + 1:02d}.pdf", relative_storage_path, 1),
            ).fetchone()
            documents.append(document)

        chunk_ids = []
        for index, document in enumerate(documents):
            page_text = f"long list source {index + 1} before long list hit {index + 1} after"
            source_text = f"long list hit {index + 1}"
            source_start = page_text.index(source_text)
            source_end = source_start + len(source_text)
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
                VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-long-lists')
                RETURNING id
                """,
                (document["id"], page["id"], source_text, source_start, source_end, zero_vector),
            ).fetchone()
            chunk_ids.append((chunk["id"], document["id"], source_text))

        question_ids: list[int] = []
        for index in range(20):
            question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, %s, 'completed', now() - (%s || ' minutes')::interval, now() - (%s || ' minutes')::interval)
                RETURNING id
                """,
                (active_project_id, f"长列表历史题目 {index + 1:02d}：请定位对应资料来源。", index, index),
            ).fetchone()
            question_ids.append(question["id"])

        active_question_id = question_ids[0]
        for rank, (chunk_id, document_id, source_text) in enumerate(chunk_ids, start=1):
            conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, %s, %s, 'strong', 'long list fixture', %s, 'before ', ' after')
                """,
                (active_question_id, chunk_id, document_id, 0.95 - rank * 0.03, rank, source_text),
            )

        conn.commit()

    print(
        json.dumps(
            {
                "project_id": active_project_id,
                "project_name": f"长列表项目 {suffix}-20",
                "question_id": active_question_id,
                "project_ids": project_ids,
                "document_ids": [document["id"] for document in documents],
                "question_ids": question_ids,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
