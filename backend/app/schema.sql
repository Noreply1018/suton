CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS projects (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL DEFAULT 'application/pdf',
  storage_path TEXT NOT NULL,
  page_count INTEGER,
  status TEXT NOT NULL CHECK (status IN ('uploaded', 'processing', 'completed', 'failed', 'unsupported')),
  failure_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS document_pages (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_no INTEGER NOT NULL CHECK (page_no > 0),
  raw_text TEXT NOT NULL,
  UNIQUE(document_id, page_no)
);

CREATE TABLE IF NOT EXISTS chunks (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_id BIGINT NOT NULL REFERENCES document_pages(id) ON DELETE CASCADE,
  page_no INTEGER NOT NULL CHECK (page_no > 0),
  text TEXT NOT NULL,
  section_title TEXT,
  embedding vector(1024) NOT NULL,
  embedding_provider TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension = 1024),
  embedding_call TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
  ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS questions (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  text TEXT NOT NULL CHECK (length(trim(text)) > 0),
  status TEXT NOT NULL CHECK (status IN ('searching', 'completed', 'no_results', 'blocked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS question_matches (
  id BIGSERIAL PRIMARY KEY,
  question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  score DOUBLE PRECISION NOT NULL,
  rank INTEGER NOT NULL CHECK (rank > 0),
  hit_reason TEXT NOT NULL,
  source_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(question_id, rank)
);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
UPDATE projects SET workspace_id = 'local-default' WHERE workspace_id IS NULL;
UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL;
ALTER TABLE projects ALTER COLUMN workspace_id SET DEFAULT 'local-default';
ALTER TABLE projects ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE projects ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE projects ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS extractable_page_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_quality TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS searchable BOOLEAN;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_stage TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS failed_stage TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS failure_code TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
UPDATE documents
SET
  extractable_page_count = COALESCE(extractable_page_count, 0),
  chunk_count = COALESCE(chunk_count, 0),
  text_quality = COALESCE(text_quality, 'unsearchable'),
  searchable = COALESCE(searchable, false),
  processing_stage = COALESCE(processing_stage, CASE WHEN status = 'completed' THEN 'completed' WHEN status IN ('failed', 'unsupported') THEN 'failed' ELSE 'uploaded' END),
  updated_at = COALESCE(updated_at, COALESCE(processed_at, created_at));
ALTER TABLE documents ALTER COLUMN extractable_page_count SET DEFAULT 0;
ALTER TABLE documents ALTER COLUMN extractable_page_count SET NOT NULL;
ALTER TABLE documents ALTER COLUMN chunk_count SET DEFAULT 0;
ALTER TABLE documents ALTER COLUMN chunk_count SET NOT NULL;
ALTER TABLE documents ALTER COLUMN text_quality SET DEFAULT 'unsearchable';
ALTER TABLE documents ALTER COLUMN text_quality SET NOT NULL;
ALTER TABLE documents ALTER COLUMN searchable SET DEFAULT false;
ALTER TABLE documents ALTER COLUMN searchable SET NOT NULL;
ALTER TABLE documents ALTER COLUMN processing_stage SET DEFAULT 'uploaded';
ALTER TABLE documents ALTER COLUMN processing_stage SET NOT NULL;
ALTER TABLE documents ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE documents ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE document_pages ADD COLUMN IF NOT EXISTS normalized_text TEXT;
ALTER TABLE document_pages ADD COLUMN IF NOT EXISTS char_count INTEGER;
ALTER TABLE document_pages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
UPDATE document_pages
SET
  normalized_text = COALESCE(normalized_text, btrim(regexp_replace(raw_text, '[ \t]+', ' ', 'g'))),
  char_count = COALESCE(char_count, length(COALESCE(normalized_text, btrim(regexp_replace(raw_text, '[ \t]+', ' ', 'g'))))),
  created_at = COALESCE(created_at, now());
ALTER TABLE document_pages ALTER COLUMN normalized_text SET DEFAULT '';
ALTER TABLE document_pages ALTER COLUMN normalized_text SET NOT NULL;
ALTER TABLE document_pages ALTER COLUMN char_count SET DEFAULT 0;
ALTER TABLE document_pages ALTER COLUMN char_count SET NOT NULL;
ALTER TABLE document_pages ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE document_pages ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_start_char INTEGER;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_end_char INTEGER;
UPDATE chunks
SET
  page_start_char = CASE WHEN position(text in p.normalized_text) > 0 THEN position(text in p.normalized_text) - 1 ELSE COALESCE(page_start_char, 0) END,
  page_end_char = CASE WHEN position(text in p.normalized_text) > 0 THEN position(text in p.normalized_text) - 1 + length(text) ELSE COALESCE(page_end_char, length(text)) END
FROM document_pages p
WHERE p.id = chunks.page_id;
UPDATE chunks
SET
  page_start_char = COALESCE(page_start_char, 0),
  page_end_char = COALESCE(page_end_char, length(text))
WHERE page_start_char IS NULL OR page_end_char IS NULL;
ALTER TABLE chunks ALTER COLUMN page_start_char SET NOT NULL;
ALTER TABLE chunks ALTER COLUMN page_end_char SET NOT NULL;

WITH document_stats AS (
  SELECT
    d.id,
    COUNT(DISTINCT CASE WHEN dp.char_count > 0 THEN dp.id END)::int AS extractable_page_count,
    COUNT(DISTINCT dp.id)::int AS stored_page_count,
    COUNT(DISTINCT c.id)::int AS chunk_count
  FROM documents d
  LEFT JOIN document_pages dp ON dp.document_id = d.id
  LEFT JOIN chunks c ON c.document_id = d.id
  GROUP BY d.id
)
UPDATE documents d
SET
  page_count = COALESCE(d.page_count, document_stats.stored_page_count),
  extractable_page_count = document_stats.extractable_page_count,
  chunk_count = document_stats.chunk_count,
  text_quality = CASE
    WHEN COALESCE(d.page_count, document_stats.stored_page_count, 0) <= 0 OR document_stats.extractable_page_count = 0 THEN 'unsearchable'
    WHEN document_stats.extractable_page_count::double precision / COALESCE(d.page_count, document_stats.stored_page_count) >= 0.90 THEN 'good'
    WHEN document_stats.extractable_page_count::double precision / COALESCE(d.page_count, document_stats.stored_page_count) >= 0.50 THEN 'fair'
    ELSE 'poor'
  END,
  searchable = CASE
    WHEN d.status = 'completed'
      AND document_stats.chunk_count > 0
      AND COALESCE(d.page_count, document_stats.stored_page_count, 0) > 0
      AND document_stats.extractable_page_count > 0 THEN true
    ELSE false
  END
FROM document_stats
WHERE document_stats.id = d.id;

ALTER TABLE questions ADD COLUMN IF NOT EXISTS failure_code TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS last_search_at TIMESTAMPTZ;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_status_check;
UPDATE questions SET status = 'no_reliable_source' WHERE status = 'no_results';
UPDATE questions SET status = 'failed', failure_code = COALESCE(failure_code, 'search_failed'), failure_reason = COALESCE(failure_reason, '题目检索失败') WHERE status = 'blocked';
UPDATE questions
SET
  last_search_at = COALESCE(last_search_at, created_at),
  updated_at = COALESCE(updated_at, created_at);
ALTER TABLE questions ALTER COLUMN last_search_at SET DEFAULT now();
ALTER TABLE questions ALTER COLUMN last_search_at SET NOT NULL;
ALTER TABLE questions ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE questions ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE question_matches ADD COLUMN IF NOT EXISTS document_id BIGINT;
ALTER TABLE question_matches ADD COLUMN IF NOT EXISTS page_no INTEGER;
ALTER TABLE question_matches ADD COLUMN IF NOT EXISTS confidence_level TEXT;
ALTER TABLE question_matches ADD COLUMN IF NOT EXISTS context_before TEXT;
ALTER TABLE question_matches ADD COLUMN IF NOT EXISTS context_after TEXT;
UPDATE question_matches qm
SET
  document_id = COALESCE(qm.document_id, c.document_id),
  page_no = COALESCE(qm.page_no, c.page_no),
  confidence_level = COALESCE(qm.confidence_level, CASE WHEN qm.score >= 0.72 THEN 'strong' WHEN qm.score >= 0.55 THEN 'reference' ELSE 'low' END),
  context_before = COALESCE(qm.context_before, ''),
  context_after = COALESCE(qm.context_after, '')
FROM chunks c
WHERE c.id = qm.chunk_id;
UPDATE question_matches
SET
  confidence_level = COALESCE(confidence_level, 'low'),
  context_before = COALESCE(context_before, ''),
  context_after = COALESCE(context_after, '');
ALTER TABLE question_matches ALTER COLUMN confidence_level SET DEFAULT 'low';
ALTER TABLE question_matches ALTER COLUMN confidence_level SET NOT NULL;
ALTER TABLE question_matches ALTER COLUMN context_before SET DEFAULT '';
ALTER TABLE question_matches ALTER COLUMN context_before SET NOT NULL;
ALTER TABLE question_matches ALTER COLUMN context_after SET DEFAULT '';
ALTER TABLE question_matches ALTER COLUMN context_after SET NOT NULL;
ALTER TABLE question_matches ALTER COLUMN document_id SET NOT NULL;
ALTER TABLE question_matches ALTER COLUMN page_no SET NOT NULL;

DO $$
BEGIN
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_status_check;
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_text_quality_check;
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_processing_stage_check;
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_failed_stage_check;
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_failure_code_check;
  ALTER TABLE documents ADD CONSTRAINT documents_status_check CHECK (status IN ('uploaded', 'processing', 'completed', 'failed', 'unsupported', 'deleting'));
  ALTER TABLE documents ADD CONSTRAINT documents_text_quality_check CHECK (text_quality IN ('good', 'fair', 'poor', 'unsearchable'));
  ALTER TABLE documents ADD CONSTRAINT documents_processing_stage_check CHECK (processing_stage IN ('uploaded', 'extracting_text', 'chunking', 'embedding', 'indexing', 'completed', 'failed'));
  ALTER TABLE documents ADD CONSTRAINT documents_failed_stage_check CHECK (failed_stage IS NULL OR failed_stage IN ('uploaded', 'extracting_text', 'chunking', 'embedding', 'indexing'));
  ALTER TABLE documents ADD CONSTRAINT documents_failure_code_check CHECK (failure_code IS NULL OR failure_code IN ('invalid_pdf', 'unsupported_file_type', 'no_text_layer', 'extract_text_failed', 'chunking_failed', 'embedding_failed', 'indexing_failed', 'storage_missing', 'delete_file_failed', 'unknown_processing_error'));

  ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_status_check;
  ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_failure_code_check;
  ALTER TABLE questions ADD CONSTRAINT questions_status_check CHECK (status IN ('searching', 'completed', 'no_reliable_source', 'failed'));
  ALTER TABLE questions ADD CONSTRAINT questions_failure_code_check CHECK (failure_code IS NULL OR failure_code IN ('embedding_failed', 'source_context_failed', 'search_failed'));

  ALTER TABLE question_matches DROP CONSTRAINT IF EXISTS question_matches_confidence_level_check;
  ALTER TABLE question_matches DROP CONSTRAINT IF EXISTS question_matches_document_id_fkey;
  ALTER TABLE question_matches DROP CONSTRAINT IF EXISTS question_matches_page_no_check;
  ALTER TABLE question_matches ADD CONSTRAINT question_matches_confidence_level_check CHECK (confidence_level IN ('strong', 'reference', 'low'));
  ALTER TABLE question_matches ADD CONSTRAINT question_matches_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;
  ALTER TABLE question_matches ADD CONSTRAINT question_matches_page_no_check CHECK (page_no > 0);

  ALTER TABLE chunks DROP CONSTRAINT IF EXISTS chunks_page_offsets_check;
  ALTER TABLE chunks ADD CONSTRAINT chunks_page_offsets_check CHECK (page_start_char >= 0 AND page_end_char >= page_start_char);
END $$;
