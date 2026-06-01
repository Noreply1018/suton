from __future__ import annotations

import os
from pathlib import Path
import runpy
import time

from app.db import connect, vector_literal
from app.processing import confidence_level_for_score

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


def main() -> None:
    check = os.getenv("CHECK", "schema-v0.1.0")
    checks = {
        "schema-v0.1.0": check_schema,
        "v020-schema": check_v020_schema,
        "v020-project-name-migration": check_v020_project_name_migration,
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
    }
    if check not in checks:
        raise SystemExit(f"unsupported CHECK={check}")
    checks[check]()
    print(f"CHECK={check} passed")


if __name__ == "__main__":
    main()
