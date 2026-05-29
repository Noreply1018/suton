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
