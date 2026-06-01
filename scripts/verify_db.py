from __future__ import annotations

import os
from pathlib import Path
import runpy
import shutil
import time

from app.config import settings
from app.db import connect, vector_literal
from app.processing import (
    confidence_level_for_score,
    document_searchable_for_fields,
    process_document,
    research_question_with_embedding,
    reset_document_for_reprocess,
    text_quality_for_counts,
)

migrated_project_name = runpy.run_path("scripts/migrate.py")["migrated_project_name"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def scalar(sql: str, params: tuple = ()) -> int:
    with connect() as conn:
        return conn.execute(sql, params).fetchone()["value"]


def check_schema() -> None:
    required_tables = {"projects", "documents", "document_pages", "chunks", "questions", "question_matches"}
    required_columns = {
        "projects": {"id", "name", "created_at"},
        "documents": {
            "id",
            "project_id",
            "filename",
            "content_type",
            "storage_path",
            "page_count",
            "status",
            "failure_reason",
            "created_at",
            "processed_at",
        },
        "document_pages": {"id", "document_id", "page_no", "raw_text"},
        "chunks": {
            "id",
            "document_id",
            "page_id",
            "page_no",
            "text",
            "section_title",
            "embedding",
            "embedding_provider",
            "embedding_model",
            "embedding_dimension",
            "embedding_call",
            "created_at",
        },
        "questions": {"id", "project_id", "text", "status", "created_at"},
        "question_matches": {"id", "question_id", "chunk_id", "score", "rank", "hit_reason", "source_text", "created_at"},
    }
    with connect() as conn:
        table_rows = conn.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        ).fetchall()
        column_rows = conn.execute(
            """
            SELECT table_name, column_name FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        ).fetchall()
        vector_installed = conn.execute("SELECT COUNT(*) AS value FROM pg_extension WHERE extname = 'vector'").fetchone()["value"]
    present_tables = {row["table_name"] for row in table_rows}
    missing_tables = required_tables - present_tables
    require(not missing_tables, f"missing tables: {sorted(missing_tables)}")
    present_columns: dict[str, set[str]] = {}
    for row in column_rows:
        present_columns.setdefault(row["table_name"], set()).add(row["column_name"])
    for table, expected_columns in required_columns.items():
        missing_columns = expected_columns - present_columns.get(table, set())
        require(not missing_columns, f"missing columns in {table}: {sorted(missing_columns)}")
    require(vector_installed == 1, "pgvector extension is not installed")


def check_v020_schema() -> None:
    required_tables = {"projects", "documents", "document_pages", "chunks", "questions", "question_matches"}
    required_columns = {
        "projects": {"id", "workspace_id", "name", "created_at", "updated_at"},
        "documents": {
            "id",
            "project_id",
            "filename",
            "content_type",
            "storage_path",
            "page_count",
            "extractable_page_count",
            "chunk_count",
            "text_quality",
            "searchable",
            "status",
            "processing_stage",
            "failed_stage",
            "failure_code",
            "failure_reason",
            "created_at",
            "processed_at",
            "updated_at",
        },
        "document_pages": {"id", "document_id", "page_no", "raw_text", "normalized_text", "char_count", "created_at"},
        "chunks": {
            "id",
            "document_id",
            "page_id",
            "page_no",
            "text",
            "page_start_char",
            "page_end_char",
            "embedding",
            "embedding_provider",
            "embedding_model",
            "embedding_dimension",
            "embedding_call",
            "created_at",
        },
        "questions": {"id", "project_id", "text", "status", "failure_code", "failure_reason", "last_search_at", "created_at", "updated_at"},
        "question_matches": {
            "id",
            "question_id",
            "chunk_id",
            "document_id",
            "page_no",
            "score",
            "rank",
            "confidence_level",
            "hit_reason",
            "source_text",
            "context_before",
            "context_after",
            "created_at",
        },
    }
    required_constraints = {
        "documents_status_check",
        "documents_text_quality_check",
        "documents_processing_stage_check",
        "documents_failed_stage_check",
        "documents_failure_code_check",
        "questions_status_check",
        "questions_failure_code_check",
        "chunks_embedding_dimension_check",
        "question_matches_confidence_level_check",
        "question_matches_document_id_fkey",
        "question_matches_page_no_check",
        "chunks_page_offsets_check",
    }
    required_foreign_keys = {
        ("documents", "project_id", "projects"),
        ("document_pages", "document_id", "documents"),
        ("chunks", "document_id", "documents"),
        ("chunks", "page_id", "document_pages"),
        ("questions", "project_id", "projects"),
        ("question_matches", "question_id", "questions"),
        ("question_matches", "chunk_id", "chunks"),
        ("question_matches", "document_id", "documents"),
    }
    expected_constraint_fragments = {
        "documents_status_check": ["uploaded", "processing", "completed", "failed", "unsupported", "deleting"],
        "documents_text_quality_check": ["good", "fair", "poor", "unsearchable"],
        "documents_processing_stage_check": ["uploaded", "extracting_text", "chunking", "embedding", "indexing", "completed", "failed"],
        "documents_failed_stage_check": ["uploaded", "extracting_text", "chunking", "embedding", "indexing"],
        "documents_failure_code_check": [
            "invalid_pdf",
            "unsupported_file_type",
            "no_text_layer",
            "extract_text_failed",
            "chunking_failed",
            "embedding_failed",
            "indexing_failed",
            "storage_missing",
            "delete_file_failed",
            "unknown_processing_error",
        ],
        "questions_status_check": ["searching", "completed", "no_reliable_source", "failed"],
        "questions_failure_code_check": ["embedding_failed", "source_context_failed", "search_failed"],
        "chunks_embedding_dimension_check": ["embedding_dimension", "1024"],
        "question_matches_confidence_level_check": ["strong", "reference", "low"],
        "question_matches_page_no_check": ["page_no", "> 0"],
        "chunks_page_offsets_check": ["page_start_char >= 0", "page_end_char >= page_start_char"],
    }
    with connect() as conn:
        table_rows = conn.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        ).fetchall()
        column_rows = conn.execute(
            """
            SELECT table_name, column_name FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        ).fetchall()
        constraint_rows = conn.execute(
            """
            SELECT con.conname AS constraint_name, pg_get_constraintdef(con.oid) AS constraint_definition
            FROM pg_constraint con
            JOIN pg_namespace nsp ON nsp.oid = con.connamespace
            WHERE nsp.nspname = 'public'
            """
        ).fetchall()
        unique_index_count = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'projects'
              AND indexname = 'projects_workspace_name_unique'
              AND indexdef ILIKE '%UNIQUE%'
              AND indexdef ILIKE '%workspace_id%'
              AND indexdef ILIKE '%name%'
            """
        ).fetchone()["value"]
        foreign_key_rows = conn.execute(
            """
            SELECT
              tc.table_name,
              kcu.column_name,
              ccu.table_name AS referenced_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.constraint_type = 'FOREIGN KEY'
            """
        ).fetchall()
        embedding_type = conn.execute(
            """
            SELECT format_type(a.atttypid, a.atttypmod) AS value
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = 'chunks'
              AND a.attname = 'embedding'
              AND NOT a.attisdropped
            """
        ).fetchone()["value"]
        not_null_rows = conn.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND is_nullable = 'NO'
            """
        ).fetchall()
        incompatible_completed_documents = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM documents d
            LEFT JOIN (
              SELECT
                document_id,
                COUNT(*)::int AS chunk_count,
                COUNT(DISTINCT page_id)::int AS extractable_page_count
              FROM chunks
              GROUP BY document_id
            ) c ON c.document_id = d.id
            WHERE d.status = 'completed'
              AND COALESCE(c.chunk_count, 0) > 0
              AND (
                d.searchable IS NOT TRUE
                OR d.text_quality = 'unsearchable'
                OR d.chunk_count <> c.chunk_count
                OR d.extractable_page_count <> c.extractable_page_count
              )
            """
        ).fetchone()["value"]
        invalid_page_stats = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM document_pages
            WHERE char_count <> length(normalized_text)
              OR normalized_text <> btrim(regexp_replace(raw_text, '[ \t]+', ' ', 'g'))
            """
        ).fetchone()["value"]
        invalid_chunk_offsets = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM chunks c
            JOIN document_pages p ON p.id = c.page_id
            WHERE c.page_start_char < 0
              OR c.page_end_char < c.page_start_char
              OR c.page_end_char > length(p.normalized_text)
              OR substring(p.normalized_text from c.page_start_char + 1 for c.page_end_char - c.page_start_char) <> c.text
            """
        ).fetchone()["value"]
        inconsistent_matches = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            WHERE qm.document_id <> c.document_id
              OR qm.page_no <> c.page_no
            """
        ).fetchone()["value"]
        invalid_document_health = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM documents
            WHERE extractable_page_count > COALESCE(page_count, 0)
              OR text_quality <> CASE
                WHEN COALESCE(page_count, 0) <= 0 OR extractable_page_count = 0 THEN 'unsearchable'
                WHEN extractable_page_count::double precision / page_count >= 0.90 THEN 'good'
                WHEN extractable_page_count::double precision / page_count >= 0.50 THEN 'fair'
                ELSE 'poor'
              END
              OR searchable <> (
                status = 'completed'
                AND chunk_count > 0
                AND text_quality <> 'unsearchable'
              )
            """
        ).fetchone()["value"]
        non_monotonic_chunk_offsets = conn.execute(
            """
            WITH ordered_chunks AS (
              SELECT
                page_id,
                id,
                page_start_char,
                LAG(page_end_char) OVER (PARTITION BY page_id ORDER BY id) AS previous_end
              FROM chunks
            )
            SELECT COUNT(*) AS value
            FROM ordered_chunks
            WHERE previous_end IS NOT NULL
              AND page_start_char < previous_end
            """
        ).fetchone()["value"]
        vector_installed = conn.execute("SELECT COUNT(*) AS value FROM pg_extension WHERE extname = 'vector'").fetchone()["value"]
    present_tables = {row["table_name"] for row in table_rows}
    require(not (required_tables - present_tables), f"missing v0.2.0 tables: {sorted(required_tables - present_tables)}")
    present_columns: dict[str, set[str]] = {}
    for row in column_rows:
        present_columns.setdefault(row["table_name"], set()).add(row["column_name"])
    for table, expected_columns in required_columns.items():
        missing_columns = expected_columns - present_columns.get(table, set())
        require(not missing_columns, f"missing v0.2.0 columns in {table}: {sorted(missing_columns)}")
    present_constraints = {row["constraint_name"] for row in constraint_rows}
    missing_constraints = required_constraints - present_constraints
    require(not missing_constraints, f"missing v0.2.0 constraints: {sorted(missing_constraints)}")
    constraint_definitions = {row["constraint_name"]: row["constraint_definition"] for row in constraint_rows}
    for constraint_name, fragments in expected_constraint_fragments.items():
        definition = constraint_definitions.get(constraint_name, "")
        missing_fragments = [fragment for fragment in fragments if fragment not in definition]
        require(not missing_fragments, f"constraint {constraint_name} missing fragments: {missing_fragments}")
    present_foreign_keys = {(row["table_name"], row["column_name"], row["referenced_table"]) for row in foreign_key_rows}
    missing_foreign_keys = required_foreign_keys - present_foreign_keys
    require(not missing_foreign_keys, f"missing v0.2.0 foreign keys: {sorted(missing_foreign_keys)}")
    not_null_columns = {(row["table_name"], row["column_name"]) for row in not_null_rows}
    require(("question_matches", "document_id") in not_null_columns, "question_matches.document_id must be NOT NULL")
    require(("question_matches", "page_no") in not_null_columns, "question_matches.page_no must be NOT NULL")
    require(unique_index_count == 1, "projects(workspace_id, name) unique index missing")
    require(vector_installed == 1, "pgvector extension is not installed")
    require(embedding_type == "vector(1024)", f"chunks.embedding expected vector(1024), got {embedding_type}")
    require(incompatible_completed_documents == 0, "completed searchable document compatibility fields are inconsistent")
    require(invalid_page_stats == 0, "document_pages normalized_text or char_count is inconsistent with raw_text")
    require(invalid_document_health == 0, "document health fields are inconsistent")
    require(invalid_chunk_offsets == 0, "chunk offsets are inconsistent with normalized page text")
    require(non_monotonic_chunk_offsets == 0, "chunk offsets are not monotonic within page chunk order")
    require(inconsistent_matches == 0, "question_matches denormalized source fields are inconsistent with chunks")


def check_v020_project_name_migration() -> None:
    fixtures = [
        (1, "  高性能计算期末  ", "高性能计算期末"),
        (2, "", "迁移项目 2"),
        (3, None, "迁移项目 3"),
        (4, "课" * 90, "课" * 80),
        (5, "重复项目", "重复项目"),
        (6, " 重复项目 ", "重复项目（迁移 2）"),
        (7, "重复项目", "重复项目（迁移 3）"),
    ]
    used: set[str] = set()
    for project_id, raw_name, expected_name in fixtures:
        migrated_name = migrated_project_name(project_id, raw_name, used)
        require(migrated_name == expected_name, f"project migration name mismatch for {project_id}: {migrated_name!r}")
        require(1 <= len(migrated_name) <= 80, f"project migration name length out of range for {project_id}")

    long_duplicate_base = "长" * 80
    used = {long_duplicate_base, ("长" * 74) + "（迁移 2）"}
    migrated_name = migrated_project_name(8, long_duplicate_base, used)
    require(migrated_name == ("长" * 74) + "（迁移 3）", f"long duplicate suffix mismatch: {migrated_name!r}")
    require(len(migrated_name) == 80, "long duplicate migration name must remain 80 characters")

    with connect() as conn:
        invalid_names = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM projects
            WHERE length(name) < 1
               OR length(name) > 80
               OR name <> btrim(name)
            """
        ).fetchone()["value"]
        duplicate_names = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM (
              SELECT workspace_id, name
              FROM projects
              GROUP BY workspace_id, name
              HAVING COUNT(*) > 1
            ) duplicates
            """
        ).fetchone()["value"]
        missing_workspace = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM projects
            WHERE workspace_id <> 'local-default'
               OR workspace_id IS NULL
               OR updated_at IS NULL
            """
        ).fetchone()["value"]
    require(invalid_names == 0, "migrated projects contain empty, overlong, or untrimmed names")
    require(duplicate_names == 0, "migrated projects contain duplicate names within workspace")
    require(missing_workspace == 0, "migrated projects are missing workspace_id or updated_at")


def check_v020_document_health_fields() -> None:
    suffix = f"{os.getpid()}-{time.time_ns()}"
    cases = [
        ("good", 10, 10, 2, "completed"),
        ("fair", 10, 5, 2, "completed"),
        ("poor", 10, 4, 2, "completed"),
        ("unsearchable", 10, 0, 0, "completed"),
        ("zero-page", 0, 0, 0, "completed"),
        ("no-chunks", 10, 10, 0, "completed"),
        ("processing", 10, 10, 2, "processing"),
    ]
    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-document-health-{suffix}",)).fetchone()
        for label, page_count, extractable_page_count, chunk_count, status in cases:
            text_quality = text_quality_for_counts(extractable_page_count, page_count)
            searchable = document_searchable_for_fields(status, chunk_count, text_quality)
            conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, %s, 'application/pdf', %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    project["id"],
                    f"{label}.pdf",
                    f"uploads/{label}.pdf",
                    page_count,
                    extractable_page_count,
                    chunk_count,
                    text_quality,
                    searchable,
                    status,
                    "completed" if status == "completed" else "embedding",
                ),
            )
        conn.commit()
        fixture_rows = conn.execute(
            """
            SELECT filename, page_count, extractable_page_count, chunk_count, text_quality, searchable, status
            FROM documents
            WHERE project_id = %s
            ORDER BY id
            """,
            (project["id"],),
        ).fetchall()
        conn.execute("DELETE FROM projects WHERE id = %s", (project["id"],))
        conn.commit()

        invalid_documents = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM documents
            WHERE extractable_page_count > COALESCE(page_count, 0)
               OR text_quality <> CASE
                 WHEN COALESCE(page_count, 0) <= 0 OR extractable_page_count = 0 THEN 'unsearchable'
                 WHEN extractable_page_count::double precision / page_count >= 0.90 THEN 'good'
                 WHEN extractable_page_count::double precision / page_count >= 0.50 THEN 'fair'
                 ELSE 'poor'
               END
               OR searchable <> (
                 status = 'completed'
                 AND chunk_count > 0
                 AND text_quality <> 'unsearchable'
               )
            """
        ).fetchone()["value"]

    require(len(fixture_rows) == len(cases), "document health fixture row count mismatch")
    expected_by_filename = {
        f"{label}.pdf": (
            text_quality_for_counts(extractable_page_count, page_count),
            document_searchable_for_fields(status, chunk_count, text_quality_for_counts(extractable_page_count, page_count)),
        )
        for label, page_count, extractable_page_count, chunk_count, status in cases
    }
    for row in fixture_rows:
        expected_quality, expected_searchable = expected_by_filename[row["filename"]]
        require(row["text_quality"] == expected_quality, f"document text_quality mismatch for {row['filename']}")
        require(row["searchable"] is expected_searchable, f"document searchable mismatch for {row['filename']}")
        require(row["extractable_page_count"] <= row["page_count"], f"extractable pages exceed page_count for {row['filename']}")
    require(invalid_documents == 0, "document health fields are inconsistent")


def check_v020_processing_failure_fields() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    suffix = f"{os.getpid()}-{time.time_ns()}"
    fixture_path = Path("tests/fixtures/broken.pdf")
    require(fixture_path.exists(), f"broken PDF fixture not found: {fixture_path}")
    project_id: int | None = None
    document_id: int | None = None
    try:
        with connect() as conn:
            project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-processing-failure-{suffix}",)).fetchone()
            project_id = int(project["id"])
            document = conn.execute(
                """
                INSERT INTO documents (project_id, filename, content_type, storage_path, status, processing_stage)
                VALUES (%s, 'broken.pdf', 'application/pdf', %s, 'uploaded', 'uploaded')
                RETURNING id
                """,
                (project_id, str(fixture_path)),
            ).fetchone()
            document_id = int(document["id"])
            conn.commit()

        failed = False
        try:
            process_document(document_id)
        except Exception:  # noqa: BLE001
            failed = True
        require(failed, "broken PDF processing did not fail")

        with connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = %s", (document_id,)).fetchone()
        require(row is not None, "failed document row missing")
        require(row["status"] == "failed", f"failed document status mismatch: {row['status']}")
        require(row["processing_stage"] == "failed", f"failed document processing_stage mismatch: {row['processing_stage']}")
        require(row["failed_stage"] == "extracting_text", f"failed document failed_stage mismatch: {row['failed_stage']}")
        require(row["failure_code"] == "invalid_pdf", f"failed document failure_code mismatch: {row['failure_code']}")
        require(row["failure_reason"] == "PDF 文件损坏，无法读取", f"failed document failure_reason mismatch: {row['failure_reason']}")
        require(row["searchable"] is False, "failed document must not be searchable")
        require(row["processed_at"] is not None, "failed document processed_at must be set")

        client = TestClient(app)
        response = client.get(f"/documents/{document_id}")
        require(response.status_code == 200, f"failed document detail expected HTTP 200, got {response.status_code}: {response.text}")
        detail = response.json()
        require(detail["failed_stage"] == "extracting_text", "failed document detail failed_stage mismatch")
        require(detail["failure_code"] == "invalid_pdf", "failed document detail failure_code mismatch")
        require(detail["failure_reason"] == "PDF 文件损坏，无法读取", "failed document detail failure_reason mismatch")
        require(detail["processing_stage"] == "failed", "failed document detail processing_stage mismatch")
        require(detail["searchable"] is False, "failed document detail searchable mismatch")
    finally:
        if project_id is not None:
            with connect() as conn:
                conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                conn.commit()


def check_v020_processing_embedding_failure_stage() -> None:
    suffix = f"{os.getpid()}-{time.time_ns()}"
    fixture_path = Path("tests/fixtures/text-layer-material.pdf")
    require(fixture_path.exists(), f"text-layer PDF fixture not found: {fixture_path}")
    project_id: int | None = None
    original_key = settings.dashscope_api_key
    try:
        with connect() as conn:
            project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-processing-embedding-failure-{suffix}",)).fetchone()
            project_id = int(project["id"])
            document = conn.execute(
                """
                INSERT INTO documents (project_id, filename, content_type, storage_path, status, processing_stage)
                VALUES (%s, 'text-layer-material.pdf', 'application/pdf', %s, 'uploaded', 'uploaded')
                RETURNING id
                """,
                (project_id, str(fixture_path)),
            ).fetchone()
            document_id = int(document["id"])
            conn.commit()

        object.__setattr__(settings, "dashscope_api_key", None)
        failed = False
        try:
            process_document(document_id)
        except Exception:  # noqa: BLE001
            failed = True
        require(failed, "text-layer PDF processing did not fail without embedding credentials")

        with connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = %s", (document_id,)).fetchone()
            page_count = conn.execute("SELECT COUNT(*) AS value FROM document_pages WHERE document_id = %s", (document_id,)).fetchone()["value"]
            chunk_count = conn.execute("SELECT COUNT(*) AS value FROM chunks WHERE document_id = %s", (document_id,)).fetchone()["value"]
        require(row is not None, "embedding-failed document row missing")
        require(row["status"] == "failed", f"embedding-failed document status mismatch: {row['status']}")
        require(row["processing_stage"] == "failed", f"embedding-failed processing_stage mismatch: {row['processing_stage']}")
        require(row["failed_stage"] == "embedding", f"embedding-failed failed_stage mismatch: {row['failed_stage']}")
        require(row["failure_code"] == "embedding_failed", f"embedding-failed failure_code mismatch: {row['failure_code']}")
        require(row["failure_reason"] == "生成 embedding 失败", f"embedding-failed failure_reason mismatch: {row['failure_reason']}")
        require(row["page_count"] == 57, f"embedding-failed page_count mismatch: {row['page_count']}")
        require(row["extractable_page_count"] > 0, "embedding-failed extractable_page_count was not persisted")
        require(row["chunk_count"] > 0, "embedding-failed chunk_count candidate count was not persisted")
        require(row["searchable"] is False, "embedding-failed document must not be searchable")
        require(row["processed_at"] is not None, "embedding-failed processed_at must be set")
        require(page_count > 0, "embedding-failed document_pages were not persisted before embedding")
        require(chunk_count == 0, "embedding-failed document must not persist chunks without embeddings")
    finally:
        object.__setattr__(settings, "dashscope_api_key", original_key)
        if project_id is not None:
            with connect() as conn:
                conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                conn.commit()


def check_v020_document_hard_delete() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    suffix = f"{os.getpid()}-{time.time_ns()}"
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    storage_path = upload_root / f"v020-document-delete-{suffix}.pdf"
    missing_path = upload_root / f"v020-document-delete-missing-{suffix}.pdf"
    storage_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    project_id: int | None = None
    document_id: int | None = None
    missing_document_id: int | None = None
    match_id: int | None = None
    try:
        with connect() as conn:
            project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-document-delete-{suffix}",)).fetchone()
            project_id = int(project["id"])
            conn.execute("UPDATE projects SET updated_at = '2001-01-01 00:00:00+00' WHERE id = %s", (project_id,))
            before_delete_updated_at = conn.execute("SELECT updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()["updated_at"]
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, 'delete-me.pdf', 'application/pdf', %s, 1, 1, 1, 'good', true, 'completed', 'completed')
                RETURNING id
                """,
                (project_id, str(storage_path)),
            ).fetchone()
            document_id = int(document["id"])
            page = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, 1, 'delete source text', 'delete source text', 18)
                RETURNING id
                """,
                (document_id,),
            ).fetchone()
            chunk = conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char,
                  embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, 1, 'delete source', 0, 13, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-document-hard-delete')
                RETURNING id
                """,
                (document_id, page["id"], vector_literal([1.0] + [0.0] * 1023)),
            ).fetchone()
            question = conn.execute(
                "INSERT INTO questions (project_id, text, status) VALUES (%s, 'delete source query', 'completed') RETURNING id",
                (project_id,),
            ).fetchone()
            match = conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, 0.91, 1, 'strong', 'delete consistency fixture', 'delete source', '', ' text')
                RETURNING id
                """,
                (question["id"], chunk["id"], document_id),
            ).fetchone()
            match_id = int(match["id"])
            missing_document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, 'missing-delete.pdf', 'application/pdf', %s, 1, 1, 1, 'good', true, 'completed', 'completed')
                RETURNING id
                """,
                (project_id, str(missing_path)),
            ).fetchone()
            missing_document_id = int(missing_document["id"])
            conn.commit()

        client = TestClient(app)
        deleted = client.delete(f"/documents/{document_id}")
        require(deleted.status_code == 200, f"document delete expected HTTP 200, got {deleted.status_code}: {deleted.text}")
        require(deleted.json() == {"deleted": True, "document_id": document_id}, f"document delete response mismatch: {deleted.json()}")
        require(not storage_path.exists(), "deleted document file still exists")
        trash_matches = list((upload_root / ".delete-trash").glob(f"document-{document_id}-*"))
        require(not trash_matches, f"deleted document trash directory was not cleaned: {trash_matches}")

        with connect() as conn:
            document_count = conn.execute("SELECT COUNT(*) AS value FROM documents WHERE id = %s", (document_id,)).fetchone()["value"]
            page_count = conn.execute("SELECT COUNT(*) AS value FROM document_pages WHERE document_id = %s", (document_id,)).fetchone()["value"]
            chunk_count = conn.execute("SELECT COUNT(*) AS value FROM chunks WHERE document_id = %s", (document_id,)).fetchone()["value"]
            match_count = conn.execute("SELECT COUNT(*) AS value FROM question_matches WHERE id = %s", (match_id,)).fetchone()["value"]
            question_count = conn.execute("SELECT COUNT(*) AS value FROM questions WHERE project_id = %s", (project_id,)).fetchone()["value"]
            after_delete_updated_at = conn.execute("SELECT updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()["updated_at"]
        require(document_count == 0, "deleted document row still exists")
        require(page_count == 0, "deleted document pages still exist")
        require(chunk_count == 0, "deleted document chunks still exist")
        require(match_count == 0, "deleted document question_matches still exist")
        require(question_count == 1, "document delete removed question history")
        require(after_delete_updated_at > before_delete_updated_at, "document delete did not update project updated_at")

        missing = client.delete(f"/documents/{missing_document_id}")
        require(missing.status_code == 500, f"missing-file document delete expected HTTP 500, got {missing.status_code}: {missing.text}")
        require(missing.json()["detail"] == "资料文件删除失败", f"missing-file delete detail mismatch: {missing.json()}")
        with connect() as conn:
            rollback_count = conn.execute("SELECT COUNT(*) AS value FROM documents WHERE id = %s", (missing_document_id,)).fetchone()["value"]
        require(rollback_count == 1, "missing-file delete did not roll back database row")
    finally:
        if project_id is not None:
            with connect() as conn:
                conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                conn.commit()
        storage_path.unlink(missing_ok=True)


def check_v020_project_hard_delete() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    suffix = f"{os.getpid()}-{time.time_ns()}"
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    success_paths = [
        upload_root / f"v020-project-delete-{suffix}-a.pdf",
        upload_root / f"v020-project-delete-{suffix}-b.pdf",
    ]
    rollback_path = upload_root / f"v020-project-delete-rollback-{suffix}.pdf"
    missing_path = upload_root / f"v020-project-delete-missing-{suffix}.pdf"
    for path in [*success_paths, rollback_path]:
        path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    success_project_id: int | None = None
    rollback_project_id: int | None = None
    try:
        with connect() as conn:
            success_project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-project-delete-{suffix}",)).fetchone()
            success_project_id = int(success_project["id"])
            document_ids: list[int] = []
            for index, path in enumerate(success_paths, start=1):
                document = conn.execute(
                    """
                    INSERT INTO documents (
                      project_id, filename, content_type, storage_path, page_count,
                      extractable_page_count, chunk_count, text_quality, searchable,
                      status, processing_stage
                    )
                    VALUES (%s, %s, 'application/pdf', %s, 1, 1, 1, 'good', true, 'completed', 'completed')
                    RETURNING id
                    """,
                    (success_project_id, f"delete-project-{index}.pdf", str(path)),
                ).fetchone()
                document_ids.append(int(document["id"]))
                page = conn.execute(
                    """
                    INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                    VALUES (%s, 1, %s, %s, %s)
                    RETURNING id
                    """,
                    (document["id"], f"project delete source {index}", f"project delete source {index}", 23),
                ).fetchone()
                chunk = conn.execute(
                    """
                    INSERT INTO chunks (
                      document_id, page_id, page_no, text, page_start_char, page_end_char,
                      embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                    )
                    VALUES (%s, %s, 1, %s, 0, 14, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-project-hard-delete')
                    RETURNING id
                    """,
                    (document["id"], page["id"], "project delete", vector_literal([1.0] + [0.0] * 1023)),
                ).fetchone()
                if index == 1:
                    question = conn.execute(
                        "INSERT INTO questions (project_id, text, status) VALUES (%s, 'project delete query', 'completed') RETURNING id",
                        (success_project_id,),
                    ).fetchone()
                    conn.execute(
                        """
                        INSERT INTO question_matches (
                          question_id, chunk_id, document_id, page_no, score, rank,
                          confidence_level, hit_reason, source_text, context_before, context_after
                        )
                        VALUES (%s, %s, %s, 1, 0.92, 1, 'strong', 'project delete fixture', 'project delete', '', '')
                        """,
                        (question["id"], chunk["id"], document["id"]),
                    )

            rollback_project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-project-delete-rollback-{suffix}",)).fetchone()
            rollback_project_id = int(rollback_project["id"])
            for filename, path in [("rollback-good.pdf", rollback_path), ("rollback-missing.pdf", missing_path)]:
                conn.execute(
                    """
                    INSERT INTO documents (
                      project_id, filename, content_type, storage_path, page_count,
                      extractable_page_count, chunk_count, text_quality, searchable,
                      status, processing_stage
                    )
                    VALUES (%s, %s, 'application/pdf', %s, 1, 1, 1, 'good', true, 'completed', 'completed')
                    """,
                    (rollback_project_id, filename, str(path)),
                )
            conn.commit()

        client = TestClient(app)
        deleted = client.delete(f"/projects/{success_project_id}")
        require(deleted.status_code == 200, f"project delete expected HTTP 200, got {deleted.status_code}: {deleted.text}")
        require(deleted.json() == {"deleted": True, "project_id": success_project_id}, f"project delete response mismatch: {deleted.json()}")
        for path in success_paths:
            require(not path.exists(), f"deleted project file still exists: {path}")
        trash_matches = list((upload_root / ".delete-trash").glob(f"project-{success_project_id}-*"))
        require(not trash_matches, f"deleted project trash directory was not cleaned: {trash_matches}")

        with connect() as conn:
            project_count = conn.execute("SELECT COUNT(*) AS value FROM projects WHERE id = %s", (success_project_id,)).fetchone()["value"]
            document_count = conn.execute("SELECT COUNT(*) AS value FROM documents WHERE project_id = %s", (success_project_id,)).fetchone()["value"]
            page_count = conn.execute(
                "SELECT COUNT(*) AS value FROM document_pages WHERE document_id = ANY(%s)",
                (document_ids,),
            ).fetchone()["value"]
            chunk_count = conn.execute(
                "SELECT COUNT(*) AS value FROM chunks WHERE document_id = ANY(%s)",
                (document_ids,),
            ).fetchone()["value"]
            question_count = conn.execute("SELECT COUNT(*) AS value FROM questions WHERE project_id = %s", (success_project_id,)).fetchone()["value"]
            match_count = conn.execute(
                "SELECT COUNT(*) AS value FROM question_matches WHERE document_id = ANY(%s)",
                (document_ids,),
            ).fetchone()["value"]
        require(project_count == 0, "deleted project row still exists")
        require(document_count == 0, "deleted project documents still exist")
        require(page_count == 0, "deleted project pages still exist")
        require(chunk_count == 0, "deleted project chunks still exist")
        require(question_count == 0, "deleted project questions still exist")
        require(match_count == 0, "deleted project matches still exist")

        rollback = client.delete(f"/projects/{rollback_project_id}")
        require(rollback.status_code == 500, f"missing-file project delete expected HTTP 500, got {rollback.status_code}: {rollback.text}")
        require(rollback.json()["detail"] == "项目文件删除失败", f"missing-file project delete detail mismatch: {rollback.json()}")
        require(rollback_path.exists(), "project delete rollback did not restore moved file")
        rollback_trash_matches = list((upload_root / ".delete-trash").glob(f"project-{rollback_project_id}-*"))
        require(not rollback_trash_matches, f"rollback project trash directory was not cleaned: {rollback_trash_matches}")
        with connect() as conn:
            rollback_project_count = conn.execute("SELECT COUNT(*) AS value FROM projects WHERE id = %s", (rollback_project_id,)).fetchone()["value"]
            rollback_document_count = conn.execute("SELECT COUNT(*) AS value FROM documents WHERE project_id = %s", (rollback_project_id,)).fetchone()["value"]
        require(rollback_project_count == 1, "project delete failure did not roll back project row")
        require(rollback_document_count == 2, "project delete failure did not roll back document rows")

        missing_project = client.delete("/projects/999999999")
        require(missing_project.status_code == 404, f"missing project delete expected HTTP 404, got {missing_project.status_code}: {missing_project.text}")
        require(missing_project.json()["detail"] == "项目不存在", f"missing project delete detail mismatch: {missing_project.json()}")
    finally:
        if rollback_project_id is not None:
            with connect() as conn:
                conn.execute("DELETE FROM projects WHERE id = %s", (rollback_project_id,))
                conn.commit()
        for path in [*success_paths, rollback_path]:
            path.unlink(missing_ok=True)


def check_v020_delete_consistency() -> None:
    check_v020_project_hard_delete()
    check_v020_document_hard_delete()
    with connect() as conn:
        stale_matches = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM question_matches qm
            LEFT JOIN chunks c ON c.id = qm.chunk_id
            LEFT JOIN documents d ON d.id = qm.document_id
            WHERE c.id IS NULL
               OR d.id IS NULL
               OR d.status <> 'completed'
               OR d.searchable IS NOT TRUE
            """
        ).fetchone()["value"]
        mismatched_matches = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            WHERE qm.document_id <> c.document_id
               OR qm.page_no <> c.page_no
            """
        ).fetchone()["value"]
    require(stale_matches == 0, "question_matches include stale or unavailable sources")
    require(mismatched_matches == 0, "question_matches source denormalization is inconsistent after delete checks")


def check_v020_delete_trash_cleanup() -> None:
    check_v020_delete_consistency()
    upload_root = Path(settings.upload_dir).resolve()
    trash_root = upload_root / ".delete-trash"
    trash_root.mkdir(parents=True, exist_ok=True)
    empty_residual = trash_root / f"document-0-{time.time_ns()}"
    empty_residual.mkdir()
    cleanup_delete_trash(trash_root)
    require(not empty_residual.exists(), "empty delete trash operation directory was not cleaned")
    leftovers = [path for path in trash_root.iterdir() if path.name != ".gitkeep"] if trash_root.exists() else []
    require(not leftovers, f"delete trash contains unexpected leftovers: {leftovers}")


def cleanup_delete_trash(trash_root: Path) -> None:
    if not trash_root.exists():
        return
    failures: list[str] = []
    for entry in sorted(trash_root.iterdir()):
        if entry.name == ".gitkeep":
            continue
        if not entry.is_dir() or not is_delete_operation_dir(entry.name):
            failures.append(str(entry))
            continue
        files = [path for path in entry.rglob("*") if path.is_file()]
        if files:
            failures.extend(str(path) for path in files)
            continue
        shutil.rmtree(entry)
    require(not failures, f"delete trash contains recoverable or untraceable leftovers: {failures}")


def is_delete_operation_dir(name: str) -> bool:
    parts = name.split("-")
    return len(parts) == 3 and parts[0] in {"project", "document"} and parts[1].isdigit() and parts[2].isdigit()


def check_v020_document_reprocess_no_duplicates() -> None:
    suffix = f"{os.getpid()}-{time.time_ns()}"
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    storage_path = upload_root / f"v020-document-reprocess-{suffix}.pdf"
    project_id: int | None = None
    document_id: int | None = None
    question_id: int | None = None
    old_match_ids: list[int] = []
    try:
        storage_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
        with connect() as conn:
            project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-document-reprocess-{suffix}",)).fetchone()
            project_id = project["id"]
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage, processed_at
                )
                VALUES (%s, 'reprocess.pdf', 'application/pdf', %s, 1, 1, 2, 'good', true, 'completed', 'completed', now())
                RETURNING id
                """,
                (project_id, str(storage_path)),
            ).fetchone()
            document_id = document["id"]
            page = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, 1, 'old alpha old beta', 'old alpha old beta', 18)
                RETURNING id
                """,
                (document_id,),
            ).fetchone()
            chunks = []
            for rank, text in enumerate(["old alpha", "old beta"], start=1):
                start = "old alpha old beta".index(text)
                chunk = conn.execute(
                    """
                    INSERT INTO chunks (
                      document_id, page_id, page_no, text, page_start_char, page_end_char,
                      embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                    )
                    VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-document-reprocess-no-duplicates')
                    RETURNING id
                    """,
                    (document_id, page["id"], text, start, start + len(text), vector_literal([1.0, 0.0] + [0.0] * 1022)),
                ).fetchone()
                chunks.append((rank, chunk))
            question = conn.execute(
                "INSERT INTO questions (project_id, text, status) VALUES (%s, 'reprocess question', 'completed') RETURNING id",
                (project_id,),
            ).fetchone()
            question_id = question["id"]
            for rank, chunk in chunks:
                match = conn.execute(
                    """
                    INSERT INTO question_matches (
                      question_id, chunk_id, document_id, page_no, score, rank,
                      confidence_level, hit_reason, source_text, context_before, context_after
                    )
                    VALUES (%s, %s, %s, 1, 0.88, %s, 'strong', 'old reprocess fixture', 'old', '', '')
                    RETURNING id
                    """,
                    (question_id, chunk["id"], document_id, rank),
                ).fetchone()
                old_match_ids.append(match["id"])
            conn.execute("UPDATE projects SET updated_at = '2001-01-01 00:00:00+00' WHERE id = %s", (project_id,))
            conn.commit()

        require(document_id is not None and question_id is not None, "document reprocess fixture setup failed")
        reset_document_for_reprocess(document_id)
        require(storage_path.exists(), "document reprocess moved or deleted original uploaded PDF")
        with connect() as conn:
            saved_document = conn.execute("SELECT * FROM documents WHERE id = %s", (document_id,)).fetchone()
            page_count = conn.execute("SELECT COUNT(*) AS value FROM document_pages WHERE document_id = %s", (document_id,)).fetchone()["value"]
            chunk_count = conn.execute("SELECT COUNT(*) AS value FROM chunks WHERE document_id = %s", (document_id,)).fetchone()["value"]
            match_count = conn.execute("SELECT COUNT(*) AS value FROM question_matches WHERE document_id = %s", (document_id,)).fetchone()["value"]
            old_match_count = conn.execute("SELECT COUNT(*) AS value FROM question_matches WHERE id = ANY(%s)", (old_match_ids,)).fetchone()["value"]
            question_count = conn.execute("SELECT COUNT(*) AS value FROM questions WHERE id = %s", (question_id,)).fetchone()["value"]
            project_updated_at = conn.execute("SELECT updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()["updated_at"]
        require(saved_document["status"] == "uploaded", "reprocess did not reset document status to uploaded")
        require(saved_document["processing_stage"] == "uploaded", "reprocess did not reset processing_stage to uploaded")
        require(saved_document["failure_code"] is None and saved_document["failure_reason"] is None and saved_document["failed_stage"] is None, "reprocess did not clear failure fields")
        require(saved_document["searchable"] is False, "reprocess document must not remain searchable before new processing")
        require(saved_document["page_count"] == 1 and saved_document["extractable_page_count"] == 1 and saved_document["chunk_count"] == 2, "reprocess did not preserve previous health counters before new processing")
        require(page_count == 0, "reprocess left old document_pages")
        require(chunk_count == 0, "reprocess left old chunks")
        require(match_count == 0 and old_match_count == 0, "reprocess left old source matches")
        require(question_count == 1, "reprocess removed question history")
        require(str(project_updated_at) > "2001-01-01", "reprocess did not update project updated_at")
    finally:
        if project_id is not None:
            with connect() as conn:
                conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                conn.commit()
        storage_path.unlink(missing_ok=True)


def check_v020_source_detail_fields() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    suffix = f"{os.getpid()}-{time.time_ns()}"
    page_text = "before source detail after"
    source_text = "source detail"
    source_start = page_text.index(source_text)
    query = [1.0, 0.0] + [0.0] * 1022
    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-source-detail-{suffix}",)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage
            )
            VALUES (%s, 'source-detail.pdf', 'application/pdf', 'uploads/source-detail.pdf', 1, 1, 1, 'good', true, 'completed', 'completed')
            RETURNING id
            """,
            (project["id"],),
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
              document_id, page_id, page_no, text, page_start_char, page_end_char,
              embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
            )
            VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-source-detail-fields')
            RETURNING id
            """,
            (
                document["id"],
                page["id"],
                source_text,
                source_start,
                source_start + len(source_text),
                vector_literal(query),
            ),
        ).fetchone()
        question = conn.execute(
            "INSERT INTO questions (project_id, text, status) VALUES (%s, 'source detail query', 'completed') RETURNING id",
            (project["id"],),
        ).fetchone()
        match = conn.execute(
            """
            INSERT INTO question_matches (
              question_id, chunk_id, document_id, page_no, score, rank,
              confidence_level, hit_reason, source_text, context_before, context_after
            )
            VALUES (%s, %s, %s, 1, 0.91, 1, 'strong', 'fixed source detail fixture', %s, 'before ', ' after')
            RETURNING id
            """,
            (question["id"], chunk["id"], document["id"], source_text),
        ).fetchone()
        conn.commit()

        client = TestClient(app)
        detail = client.get(f"/questions/{question['id']}/matches/{match['id']}")
        require(detail.status_code == 200, f"source detail expected HTTP 200, got {detail.status_code}: {detail.text}")
        body = detail.json()
        expected_fields = {
            "id",
            "question_id",
            "document_id",
            "document_filename",
            "filename",
            "page_no",
            "chunk_id",
            "score",
            "rank",
            "confidence_level",
            "confidence_label",
            "hit_reason",
            "source_text",
            "context_before",
            "context_after",
            "pdf_url",
        }
        require(set(body) == expected_fields, f"source detail fields mismatch: {sorted(body)}")
        require(body["document_id"] == document["id"], "source detail document_id mismatch")
        require(body["document_filename"] == "source-detail.pdf", "source detail document_filename mismatch")
        require(body["filename"] == "source-detail.pdf", "source detail filename mismatch")
        require(body["page_no"] == 1, "source detail page_no mismatch")
        require(body["chunk_id"] == chunk["id"], "source detail chunk_id mismatch")
        require(body["confidence_level"] == "strong", "source detail confidence_level mismatch")
        require(body["confidence_label"] == "强相关", "source detail confidence_label mismatch")
        require(body["source_text"] == source_text, "source detail source_text mismatch")
        require(body["context_before"] == "before ", "source detail context_before mismatch")
        require(body["context_after"] == " after", "source detail context_after mismatch")
        require(body["pdf_url"] == f"/documents/{document['id']}/file#page=1", "source detail pdf_url mismatch")

        question_detail = client.get(f"/questions/{question['id']}")
        require(question_detail.status_code == 200, f"question detail expected HTTP 200, got {question_detail.status_code}: {question_detail.text}")
        matches = question_detail.json()["matches"]
        expected_question_match_fields = set(expected_fields)
        expected_question_match_fields.remove("filename")
        require(len(matches) == 1, "question detail source match count mismatch")
        require(set(matches[0]) == expected_question_match_fields, f"question match fields mismatch: {sorted(matches[0])}")
        require(matches[0]["confidence_label"] == "强相关", "question match confidence_label mismatch")

        conn.execute("DELETE FROM projects WHERE id = %s", (project["id"],))
        conn.commit()
        stale = client.get(f"/questions/{question['id']}/matches/{match['id']}")
        require(stale.status_code == 404, f"stale source expected HTTP 404, got {stale.status_code}: {stale.text}")
        require(stale.json()["detail"] == "来源已失效", f"stale source detail mismatch: {stale.text}")


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
    file_arg = os.getenv("FILE")
    if file_arg:
        source = Path(file_arg)
        require(source.exists(), f"question fixture not found: {source}")
        text = source.read_text(encoding="utf-8").strip()
        require(
            scalar("SELECT COUNT(*) AS value FROM questions WHERE text = %s", (text,)) > 0,
            "question text not found",
        )
        return
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
    seed_globals = runpy.run_path("scripts/seed_missing_source.py")
    seed_globals["main"]()


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


def check_v020_confidence_levels() -> None:
    suffix = f"{os.getpid()}-{time.time_ns()}"
    query = [1.0, 0.0] + [0.0] * 1022
    candidates = [
        ("strong", [1.0, 0.0] + [0.0] * 1022),
        ("reference", [0.60, 0.80] + [0.0] * 1022),
        ("low", [0.45, 0.8930285549745876] + [0.0] * 1022),
    ]
    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-confidence-levels-{suffix}",)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage
            )
            VALUES (%s, 'confidence.pdf', 'application/pdf', 'uploads/confidence.pdf', 1, 1, 3, 'good', true, 'completed', 'completed')
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()
        page_text = "strong reference low"
        page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, %s, %s, %s)
            RETURNING id
            """,
            (document["id"], page_text, page_text, len(page_text)),
        ).fetchone()
        for expected_level, embedding in candidates:
            start = page_text.index(expected_level)
            conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char,
                  embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-confidence-levels')
                RETURNING id
                """,
                (document["id"], page["id"], expected_level, start, start + len(expected_level), vector_literal(embedding)),
            )
        question = conn.execute(
            "INSERT INTO questions (project_id, text, status) VALUES (%s, 'confidence query', 'completed') RETURNING id",
            (project["id"],),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT id, text, 1 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE document_id = %s
            ORDER BY id
            """,
            (vector_literal(query), document["id"]),
        ).fetchall()
        for rank, row in enumerate(rows, start=1):
            score = float(row["score"])
            level = confidence_level_for_score(score)
            conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, %s, %s, %s, 'v020 confidence level fixture', %s, '', '')
                """,
                (question["id"], row["id"], document["id"], score, rank, level, row["text"]),
            )
        conn.commit()
        saved_rows = conn.execute(
            """
            SELECT c.text, qm.score, qm.confidence_level
            FROM question_matches qm
            JOIN chunks c ON c.id = qm.chunk_id
            WHERE qm.question_id = %s
            ORDER BY c.id
            """,
            (question["id"],),
        ).fetchall()
        conn.execute("DELETE FROM projects WHERE id = %s", (project["id"],))
        conn.commit()
    expected = {name: name for name, _ in candidates}
    for row in saved_rows:
        score = float(row["score"])
        require(score >= 0.40, f"confidence fixture score below source threshold: {row['text']}={score}")
        require(row["confidence_level"] == expected[row["text"]], f"confidence level mismatch for {row['text']}: {row['confidence_level']}")
        require(row["confidence_level"] == confidence_level_for_score(score), f"confidence helper mismatch for {row['text']}: {score}")
    require(len(saved_rows) == 3, "confidence level fixture did not create three matches")


def check_v020_confidence_level_fields() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    suffix = f"{os.getpid()}-{time.time_ns()}"
    query = [1.0, 0.0] + [0.0] * 1022
    candidates = [
        ("strong", "强相关", [1.0, 0.0] + [0.0] * 1022),
        ("reference", "可参考", [0.60, 0.80] + [0.0] * 1022),
        ("low", "低置信", [0.45, 0.8930285549745876] + [0.0] * 1022),
    ]
    page_text = "strong reference low"
    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-confidence-fields-{suffix}",)).fetchone()
        document = conn.execute(
            """
            INSERT INTO documents (
              project_id, filename, content_type, storage_path, page_count,
              extractable_page_count, chunk_count, text_quality, searchable,
              status, processing_stage
            )
            VALUES (%s, 'confidence-fields.pdf', 'application/pdf', 'uploads/confidence-fields.pdf', 1, 1, 3, 'good', true, 'completed', 'completed')
            RETURNING id
            """,
            (project["id"],),
        ).fetchone()
        page = conn.execute(
            """
            INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
            VALUES (%s, 1, %s, %s, %s)
            RETURNING id
            """,
            (document["id"], page_text, page_text, len(page_text)),
        ).fetchone()
        rows_by_level = {}
        for expected_level, _, embedding in candidates:
            start = page_text.index(expected_level)
            chunk = conn.execute(
                """
                INSERT INTO chunks (
                  document_id, page_id, page_no, text, page_start_char, page_end_char,
                  embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                )
                VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-confidence-level-fields')
                RETURNING id, 1 - (embedding <=> %s::vector) AS score
                """,
                (
                    document["id"],
                    page["id"],
                    expected_level,
                    start,
                    start + len(expected_level),
                    vector_literal(embedding),
                    vector_literal(query),
                ),
            ).fetchone()
            rows_by_level[expected_level] = chunk
        question = conn.execute(
            "INSERT INTO questions (project_id, text, status) VALUES (%s, 'confidence fields query', 'completed') RETURNING id",
            (project["id"],),
        ).fetchone()
        for rank, (expected_level, _, _) in enumerate(candidates, start=1):
            chunk = rows_by_level[expected_level]
            score = float(chunk["score"])
            conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, %s, %s, %s, 'v020 confidence field fixture', %s, '', '')
                """,
                (
                    question["id"],
                    chunk["id"],
                    document["id"],
                    score,
                    rank,
                    confidence_level_for_score(score),
                    expected_level,
                ),
            )
        conn.commit()

        client = TestClient(app)
        response = client.get(f"/questions/{question['id']}")
        require(response.status_code == 200, f"question detail expected HTTP 200, got {response.status_code}: {response.text}")
        matches = response.json()["matches"]
        conn.execute("DELETE FROM projects WHERE id = %s", (project["id"],))
        conn.commit()

    require(len(matches) == 3, "confidence field fixture did not return three matches")
    expected_labels = {level: label for level, label, _ in candidates}
    for match in matches:
        level = match["confidence_level"]
        require(level in expected_labels, f"unexpected confidence_level returned: {level}")
        require(match["confidence_label"] == expected_labels[level], f"confidence_label mismatch for {level}: {match['confidence_label']}")
        require(match["source_text"] == level, f"confidence source_text mismatch for {level}")
        require(match["score"] >= 0.40, f"confidence field score below threshold for {level}: {match['score']}")


def check_v020_question_research_consistency() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    suffix = f"{os.getpid()}-{time.time_ns()}"
    query = [1.0, 0.0] + [0.0] * 1022
    project_id: int | None = None
    question_id: int | None = None
    old_match_id: int | None = None
    try:
        with connect() as conn:
            project = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (f"v020-question-research-{suffix}",)).fetchone()
            project_id = project["id"]
            document = conn.execute(
                """
                INSERT INTO documents (
                  project_id, filename, content_type, storage_path, page_count,
                  extractable_page_count, chunk_count, text_quality, searchable,
                  status, processing_stage
                )
                VALUES (%s, 'question-research.pdf', 'application/pdf', 'uploads/question-research.pdf', 1, 1, 3, 'good', true, 'completed', 'completed')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            page_text = "alpha beta old"
            page = conn.execute(
                """
                INSERT INTO document_pages (document_id, page_no, raw_text, normalized_text, char_count)
                VALUES (%s, 1, %s, %s, %s)
                RETURNING id
                """,
                (document["id"], page_text, page_text, len(page_text)),
            ).fetchone()
            chunks = {}
            for text, embedding in [
                ("alpha", [1.0, 0.0] + [0.0] * 1022),
                ("beta", [0.6, 0.8] + [0.0] * 1022),
                ("old", [0.0, 1.0] + [0.0] * 1022),
            ]:
                start = page_text.index(text)
                chunks[text] = conn.execute(
                    """
                    INSERT INTO chunks (
                      document_id, page_id, page_no, text, page_start_char, page_end_char,
                      embedding, embedding_provider, embedding_model, embedding_dimension, embedding_call
                    )
                    VALUES (%s, %s, 1, %s, %s, %s, %s::vector, 'dashscope', 'text-embedding-v4', 1024, 'v020-question-research-consistency')
                    RETURNING id
                    """,
                    (document["id"], page["id"], text, start, start + len(text), vector_literal(embedding)),
                ).fetchone()
            question = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, 'research query', 'completed', '2001-01-01 00:00:00+00', '2001-01-01 00:00:00+00')
                RETURNING id
                """,
                (project_id,),
            ).fetchone()
            question_id = question["id"]
            old_match = conn.execute(
                """
                INSERT INTO question_matches (
                  question_id, chunk_id, document_id, page_no, score, rank,
                  confidence_level, hit_reason, source_text, context_before, context_after
                )
                VALUES (%s, %s, %s, 1, 0.88, 1, 'strong', 'old research fixture', 'old', 'alpha beta ', '')
                RETURNING id
                """,
                (question_id, chunks["old"]["id"], document["id"]),
            ).fetchone()
            old_match_id = old_match["id"]
            conn.execute("UPDATE projects SET updated_at = '2001-01-01 00:00:00+00' WHERE id = %s", (project_id,))
            conn.commit()

        require(question_id is not None and old_match_id is not None, "question research fixture setup failed")
        research_question_with_embedding(question_id, None, query)
        client = TestClient(app)
        response = client.get(f"/questions/{question_id}")
        require(response.status_code == 200, f"researched question expected HTTP 200, got {response.status_code}: {response.text}")
        body = response.json()
        require(body["id"] == question_id, "research changed question id")
        require(body["status"] == "completed", "research did not complete question")
        require(body["failure_code"] is None, "research completed question retained failure_code")
        require(body["failure_reason"] is None, "research completed question retained failure_reason")
        matches = body["matches"]
        require(len(matches) == 2, f"research expected two current matches, got {matches!r}")
        require([match["source_text"] for match in matches] == ["alpha", "beta"], "research did not replace visible matches in rank order")
        require([match["rank"] for match in matches] == [1, 2], "research match ranks mismatch")
        require(matches[0]["confidence_level"] == "strong", "research top confidence_level mismatch")
        require(matches[1]["confidence_level"] == "reference", "research second confidence_level mismatch")
        require(all(match["question_id"] == question_id for match in matches), "research returned match for another question")

        with connect() as conn:
            counts = conn.execute(
                """
                SELECT
                  COUNT(*) FILTER (WHERE id = %s)::int AS old_match_count,
                  COUNT(*) FILTER (WHERE question_id = %s)::int AS current_match_count
                FROM question_matches
                """,
                (old_match_id, question_id),
            ).fetchone()
            saved_question = conn.execute("SELECT last_search_at, updated_at FROM questions WHERE id = %s", (question_id,)).fetchone()
            saved_project = conn.execute("SELECT updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()
            question_count = conn.execute("SELECT COUNT(*) AS value FROM questions WHERE project_id = %s", (project_id,)).fetchone()["value"]
        require(counts["old_match_count"] == 0, "research kept old question_match")
        require(counts["current_match_count"] == 2, "research did not persist exactly two current matches")
        require(question_count == 1, "research created a replacement question instead of preserving history record")
        require(str(saved_question["last_search_at"]) > "2001-01-01", "research did not update last_search_at")
        require(saved_question["updated_at"] == saved_question["last_search_at"], "research did not sync question updated_at with last_search_at")
        require(str(saved_project["updated_at"]) > "2001-01-01", "research did not update project updated_at")
    finally:
        if project_id is not None:
            with connect() as conn:
                conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                conn.commit()


def check_v020_reprocess_research_consistency() -> None:
    check_v020_document_reprocess_no_duplicates()
    check_v020_question_research_consistency()


def main() -> None:
    check = os.getenv("CHECK", "schema-v0.1.0")
    checks = {
        "schema-v0.1.0": check_schema,
        "v020-schema": check_v020_schema,
        "v020-project-name-migration": check_v020_project_name_migration,
        "v020-document-health": check_v020_document_health_fields,
        "v020-document-health-fields": check_v020_document_health_fields,
        "v020-document-hard-delete": check_v020_document_hard_delete,
        "v020-project-hard-delete": check_v020_project_hard_delete,
        "v020-delete-consistency": check_v020_delete_consistency,
        "v020-delete-trash-cleanup": check_v020_delete_trash_cleanup,
        "v020-document-reprocess-no-duplicates": check_v020_document_reprocess_no_duplicates,
        "v020-processing-failure-fields": check_v020_processing_failure_fields,
        "v020-processing-embedding-failure-stage": check_v020_processing_embedding_failure_stage,
        "v020-source-detail-fields": check_v020_source_detail_fields,
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
        "v020-confidence-levels": check_v020_confidence_levels,
        "v020-confidence-level-fields": check_v020_confidence_level_fields,
        "v020-question-research-consistency": check_v020_question_research_consistency,
        "v020-reprocess-research-consistency": check_v020_reprocess_research_consistency,
    }
    if check not in checks:
        raise SystemExit(f"unsupported CHECK={check}")
    checks[check]()
    print(f"CHECK={check} passed")


if __name__ == "__main__":
    main()
