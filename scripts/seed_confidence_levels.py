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
    storage_path = upload_root / f"{suffix}-confidence-levels.pdf"
    shutil.copyfile(repo_root / "tests/fixtures/text-layer-material.pdf", storage_path)
    relative_storage_path = storage_path.relative_to(repo_root).as_posix()
    zero_vector = "[" + ",".join(["0"] * 1024) + "]"

    sources = [
        {
            "page_no": 1,
            "text": "strong confidence source",
            "score": 0.91,
            "rank": 1,
            "level": "strong",
            "reason": "confidence strong fixture",
            "before": "strong before ",
            "after": " strong after",
        },
        {
            "page_no": 1,
            "text": "reference confidence source",
            "score": 0.63,
            "rank": 2,
            "level": "reference",
            "reason": "confidence reference fixture",
            "before": "reference before ",
            "after": " reference after",
        },
        {
            "page_no": 2,
            "text": "low confidence source",
            "score": 0.44,
            "rank": 3,
            "level": "low",
            "reason": "confidence low fixture",
            "before": "low before ",
            "after": " low after",
        },
    ]

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"置信层级项目 {suffix}",)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage, processed_at
            )
            VALUES (%s, 'confidence-levels.pdf', 'application/pdf', %s, 2, 2, 3, 'good', true, 'completed', 'completed', now())
            RETURNING id
            """,
            (project["id"], relative_storage_path),
        ).fetchone()
        page_rows = {}
        for page_no in (1, 2):
            page_text = " ".join(item["before"] + item["text"] + item["after"] for item in sources if item["page_no"] == page_no)
            page_rows[page_no] = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (document["id"], page_no, page_text, page_text, len(page_text)),
            ).fetchone()
        question = conn.execute(
            """
            INSERT INTO questions (project_id, text, status, last_search_at)
            VALUES (%s, 'confidence levels question', 'completed', now())
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()

        match_ids = []
        for item in sources:
            page_text = " ".join(source["before"] + source["text"] + source["after"] for source in sources if source["page_no"] == item["page_no"])
            start = page_text.index(item["text"])
            end = start + len(item["text"])
            chunk = conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char, embedding,
                  embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'seed-confidence-levels')
                RETURNING id
                """,
                (document["id"], page_rows[item["page_no"]]["id"], item["page_no"], item["text"], start, end, zero_vector),
            ).fetchone()
            match = conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    question["id"],
                    chunk["id"],
                    document["id"],
                    item["page_no"],
                    item["score"],
                    item["rank"],
                    item["level"],
                    item["reason"],
                    item["text"],
                    item["before"],
                    item["after"],
                ),
            ).fetchone()
            match_ids.append(match["id"])
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": f"置信层级项目 {suffix}",
                "question_id": question["id"],
                "document_id": document["id"],
                "match_ids": match_ids,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
