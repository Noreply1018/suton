SHELL := /usr/bin/env bash

export DATABASE_URL ?= postgresql://suton:suton@localhost:54329/suton
export REDIS_URL ?= redis://localhost:56379/0
export UPLOAD_DIR ?= uploads
export DASH_SCOPE_BASE_URL ?= https://dashscope.aliyuncs.com/compatible-mode/v1
export EMBEDDING_PROVIDER ?= dashscope
export EMBEDDING_MODEL ?= text-embedding-v4
export EMBEDDING_DIMENSION ?= 1024
export API_URL ?= http://127.0.0.1:8000
export NEXT_PUBLIC_API_URL ?= http://127.0.0.1:8000
export PYTHONPATH := backend

.PHONY: env-info doctor reset-demo dev start docker-build docker-prod-up docker-prod-down migrate process-demo verify-db verify-spec verify-secrets evidence-package evidence-package-with-tests verify-e2e test backend-test frontend-test install

install:
	uv sync --project backend
	pnpm install

env-info:
	uv run --project backend python scripts/env_info.py

doctor:
	uv run --project backend python scripts/doctor.py

reset-demo:
	uv run --project backend python scripts/reset_demo.py

dev:
	uv run --project backend python scripts/dev_check.py
	docker compose up -d postgres redis
	(trap 'kill 0' INT TERM EXIT; \
	 uv run --project backend rq worker suton --url "$$REDIS_URL" & \
	 uv run --project backend uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 & \
	 pnpm --filter @suton/web dev)

start:
	uv run --project backend python scripts/dev_check.py
	docker compose up -d postgres redis
	uv run --project backend python scripts/migrate.py
	uv run --project backend python scripts/doctor.py --preflight
	(trap 'kill 0' INT TERM EXIT; \
	 uv run --project backend rq worker suton --url "$$REDIS_URL" & \
	 uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 & \
	 NEXT_PUBLIC_API_URL="$$NEXT_PUBLIC_API_URL" pnpm --dir frontend exec next dev --hostname 127.0.0.1 --port 3000)

docker-build:
	docker build -t suton:local .

docker-prod-up:
	SUTON_IMAGE=suton SUTON_IMAGE_TAG=local docker compose -f docker-compose.prod.yml up -d

docker-prod-down:
	SUTON_IMAGE=suton SUTON_IMAGE_TAG=local docker compose -f docker-compose.prod.yml down

migrate:
	docker compose up -d postgres redis
	uv run --project backend python scripts/migrate.py

process-demo:
	uv run --project backend python scripts/process_demo.py

search-question:
	uv run --project backend python scripts/search_question.py

verify-db:
	uv run --project backend python scripts/verify_db.py

verify-spec:
	uv run --project backend python scripts/verify_release_gate.py

verify-secrets:
	uv run --project backend python scripts/scan_secrets.py

evidence-package:
	uv run --project backend python scripts/collect_evidence.py

evidence-package-with-tests:
	uv run --project backend python scripts/collect_evidence.py --with-tests

verify-e2e:
	uv run --project backend python scripts/dev_check.py
	docker compose up -d postgres redis
	uv run --project backend python scripts/migrate.py
	uv run --project backend python scripts/reset_demo.py
	(setsid uv run --project backend rq worker suton --url "$$REDIS_URL" & worker_pid=$$!; \
	 setsid uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 & api_pid=$$!; \
	 setsid pnpm --dir frontend exec next dev --hostname 127.0.0.1 & web_pid=$$!; \
	 cleanup() { kill -TERM -- -$$worker_pid -$$api_pid -$$web_pid 2>/dev/null || true; wait $$worker_pid $$api_pid $$web_pid 2>/dev/null || true; }; \
	 trap cleanup INT TERM EXIT; \
	 uv run --project backend python scripts/wait_http.py http://127.0.0.1:8000/health http://127.0.0.1:3000 && \
	 E2E_BASE_URL=http://127.0.0.1:3000 pnpm exec playwright test; status=$$?; cleanup; exit $$status)

test: backend-test frontend-test

backend-test:
	uv run --project backend pytest backend/tests scripts/tests

frontend-test:
	pnpm --filter @suton/web lint
	pnpm --filter @suton/web typecheck
