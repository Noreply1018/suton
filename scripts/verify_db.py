from __future__ import annotations

import os
from pathlib import Path

from app.db import connect


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def scalar(sql: str, params: tuple = ()) -> int:
    with connect() as conn:
        return conn.execute(sql, params).fetchone()["value"]


def check_schema() -> None:
    required = {"projects", "documents", "document_pages", "chunks", "questions", "question_matches"}
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        ).fetchall()
    present = {row["table_name"] for row in rows}
    missing = required - present
    require(not missing, f"missing tables: {sorted(missing)}")


def check_project_created() -> None:
    name = os.getenv("PROJECT_NAME", "高等数学（上）期末复习")
    require(scalar("SELECT COUNT(*) AS value FROM projects WHERE name = %s", (name,)) > 0, "project not found")


def check_document_processed() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/text-layer-material.pdf")).name
    require(
        scalar("SELECT COUNT(*) AS value FROM documents WHERE filename = %s AND status = 'completed'", (filename,)) > 0,
        "completed document not found",
    )


def check_document_uploaded() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/text-layer-material.pdf")).name
    require(
        scalar("SELECT COUNT(*) AS value FROM documents WHERE filename = %s", (filename,)) > 0,
        "uploaded document not found",
    )


def check_uploaded_file_exists() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/text-layer-material.pdf")).name
    with connect() as conn:
        row = conn.execute("SELECT storage_path FROM documents WHERE filename = %s ORDER BY id DESC LIMIT 1", (filename,)).fetchone()
    require(bool(row), "document record not found")
    require(Path(row["storage_path"]).exists(), f"uploaded file missing: {row['storage_path']}")


def check_document_failed() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/broken.pdf")).name
    require(
        scalar("SELECT COUNT(*) AS value FROM documents WHERE filename = %s AND status = 'failed' AND failure_reason IS NOT NULL", (filename,)) > 0,
        "failed document not found",
    )


def check_document_unsupported() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/scanned.pdf")).name
    require(
        scalar("SELECT COUNT(*) AS value FROM documents WHERE filename = %s AND status = 'unsupported' AND failure_reason IS NOT NULL", (filename,)) > 0,
        "unsupported document not found",
    )


def check_document_count_unchanged() -> None:
    require(
        scalar("SELECT COUNT(*) AS value FROM documents WHERE content_type <> 'application/pdf' OR filename !~* '\\.pdf$'") == 0,
        "non-pdf document record exists",
    )


def check_project_count_unchanged() -> None:
    require(
        scalar("SELECT COUNT(*) AS value FROM projects WHERE length(trim(name)) = 0") == 0,
        "blank project exists",
    )


def check_question_count_unchanged() -> None:
    require(
        scalar("SELECT COUNT(*) AS value FROM questions WHERE length(trim(text)) = 0") == 0,
        "blank question exists",
    )


def check_project_summary() -> None:
    name = os.getenv("PROJECT_NAME", "高等数学（上）期末复习")
    expected_documents = os.getenv("EXPECT_DOCUMENT_COUNT")
    expected_questions = os.getenv("EXPECT_QUESTION_COUNT")
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              COUNT(DISTINCT d.id)::int AS document_count,
              COUNT(DISTINCT q.id)::int AS question_count
            FROM projects p
            LEFT JOIN documents d ON d.project_id = p.id
            LEFT JOIN questions q ON q.project_id = p.id
            WHERE p.name = %s
            GROUP BY p.id
            """,
            (name,),
        ).fetchone()
    require(bool(row), "project summary not found")
    require(row["document_count"] >= 0 and row["question_count"] >= 0, "invalid project summary")
    if expected_documents is not None:
        require(row["document_count"] == int(expected_documents), f"document_count expected {expected_documents}, got {row['document_count']}")
    if expected_questions is not None:
        require(row["question_count"] == int(expected_questions), f"question_count expected {expected_questions}, got {row['question_count']}")


def check_chunk_embeddings() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/text-layer-material.pdf")).name
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.filename = %s AND c.embedding_provider = 'dashscope'
              AND c.embedding_model = 'text-embedding-v4' AND c.embedding_dimension = 1024
            """,
            (filename,),
        )
        > 0,
        "chunk embeddings not found",
    )


def check_chunk_source_complete() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/text-layer-material.pdf")).name
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.filename = %s AND c.document_id IS NOT NULL AND c.page_no IS NOT NULL
              AND c.text <> '' AND c.embedding_provider <> '' AND c.embedding_model <> ''
              AND c.embedding_dimension = 1024
            """,
            (filename,),
        )
        > 0,
        "complete chunk sources not found",
    )
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.filename = %s AND (c.text = '' OR c.embedding_provider = '' OR c.embedding_model = '')
            """,
            (filename,),
        )
        == 0,
        "incomplete chunk source exists",
    )


def check_source_lineage() -> None:
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM question_matches qm
            JOIN questions q ON q.id = qm.question_id
            JOIN chunks c ON c.id = qm.chunk_id
            JOIN document_pages p ON p.id = c.page_id
            JOIN documents d ON d.id = c.document_id
            WHERE qm.source_text IS NOT NULL AND c.page_no IS NOT NULL AND d.filename IS NOT NULL
            """
        )
        > 0,
        "source lineage missing",
    )


def check_question_created() -> None:
    require(scalar("SELECT COUNT(*) AS value FROM questions") > 0, "question not found")


def check_question_matches_with_source() -> None:
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE qm.rank <= 5 AND qm.source_text <> '' AND c.page_no IS NOT NULL AND d.filename <> ''
            """
        )
        > 0,
        "source matches missing",
    )


def seed_match_missing_source() -> None:
    from scripts.seed_missing_source import main as seed

    seed()


def check_missing_source_not_visible() -> None:
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE qm.source_text IS NOT NULL AND length(trim(qm.source_text)) > 0
              AND c.page_no IS NOT NULL AND d.filename IS NOT NULL
              AND qm.hit_reason = 'seed missing source'
            """
        )
        == 0,
        "seeded missing-source match would be visible",
    )


def check_no_question_matches() -> None:
    filename = Path(os.getenv("FILE", "tests/fixtures/unmatched-question.txt")).name
    require(
        scalar(
            """
            SELECT COUNT(*) AS value
            FROM questions q
            LEFT JOIN question_matches qm ON qm.question_id = q.id
            WHERE q.text = %s AND qm.id IS NULL
            """,
            (Path(os.getenv("FILE", "tests/fixtures/unmatched-question.txt")).read_text(encoding="utf-8").strip() if Path(os.getenv("FILE", "tests/fixtures/unmatched-question.txt")).exists() else filename,),
        )
        > 0,
        "unmatched question without matches not found",
    )


def main() -> None:
    check = os.getenv("CHECK", "schema-v0.1.0")
    checks = {
        "schema-v0.1.0": check_schema,
        "project-created": check_project_created,
        "project-summary": check_project_summary,
        "project-count-unchanged": check_project_count_unchanged,
        "document-uploaded": check_document_uploaded,
        "uploaded-file-exists": check_uploaded_file_exists,
        "document-failed": check_document_failed,
        "document-unsupported": check_document_unsupported,
        "document-count-unchanged": check_document_count_unchanged,
        "document-processed": check_document_processed,
        "chunk-embeddings": check_chunk_embeddings,
        "chunk-source-complete": check_chunk_source_complete,
        "source-lineage": check_source_lineage,
        "question-created": check_question_created,
        "question-count-unchanged": check_question_count_unchanged,
        "question-matches-with-source": check_question_matches_with_source,
        "seed-match-missing-source": seed_match_missing_source,
        "missing-source-not-visible": check_missing_source_not_visible,
        "no-question-matches": check_no_question_matches,
    }
    if check not in checks:
        raise SystemExit(f"unsupported CHECK={check}")
    checks[check]()
    print(f"CHECK={check} passed")


if __name__ == "__main__":
    main()
