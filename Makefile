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

.PHONY: env-info doctor reset-demo dev start docker-build docker-prod-up docker-prod-down migrate process-demo verify-db verify-api-contract verify-spec verify-secrets evidence-package evidence-package-with-tests verify-e2e test backend-test frontend-test v020-db-test v020-api-test install

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

verify-api-contract:
	uv run --project backend python scripts/verify_api_contract.py

verify-spec:
	uv run --project backend python scripts/verify_release_gate.py

verify-secrets:
	uv run --project backend python scripts/scan_secrets.py

evidence-package:
	uv run --project backend python scripts/collect_evidence.py

evidence-package-with-tests:
	uv run --project backend python scripts/collect_evidence.py --with-tests

verify-e2e:
	@if [[ "$$SCENARIO" == "v020-first-empty-project" ]]; then \
		uv run --project backend python scripts/dev_check.py --skip-embedding; \
	else \
		uv run --project backend python scripts/dev_check.py; \
	fi
	docker compose up -d postgres redis
	uv run --project backend python scripts/migrate.py
	uv run --project backend python scripts/reset_demo.py
	(api_port="$${E2E_API_PORT:-18000}"; web_port="$${E2E_WEB_PORT:-13000}"; \
	 api_url="http://127.0.0.1:$$api_port"; web_url="http://127.0.0.1:$$web_port"; \
	 setsid uv run --project backend rq worker suton --url "$$REDIS_URL" & worker_pid=$$!; \
	 setsid env CORS_ALLOW_ORIGINS="$$web_url" uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "$$api_port" & api_pid=$$!; \
	 setsid env NEXT_PUBLIC_API_URL="$$api_url" pnpm --dir frontend exec next dev --hostname 127.0.0.1 --port "$$web_port" & web_pid=$$!; \
	 cleanup() { kill -TERM -- -$$worker_pid -$$api_pid -$$web_pid 2>/dev/null || true; wait $$worker_pid $$api_pid $$web_pid 2>/dev/null || true; }; \
	 trap cleanup INT TERM EXIT; \
	 uv run --project backend python scripts/wait_http.py "$$api_url/health" "$$web_url" && \
	 test_args=(); if [[ -n "$$SCENARIO" ]]; then test_args=(--grep "$$SCENARIO"); fi; \
	 E2E_BASE_URL="$$web_url" NEXT_PUBLIC_API_URL="$$api_url" pnpm exec playwright test "$${test_args[@]}"; status=$$?; cleanup; exit $$status)

test: backend-test frontend-test v020-db-test v020-api-test

backend-test:
	uv run --project backend pytest backend/tests scripts/tests

frontend-test:
	pnpm --filter @suton/web lint
	pnpm --filter @suton/web typecheck

v020-db-test:
	$(MAKE) migrate
	CHECK=v020-schema $(MAKE) verify-db
	CHECK=v020-confidence-levels $(MAKE) verify-db
	CHECK=v020-confidence-level-fields $(MAKE) verify-db
	CHECK=v020-project-name-migration $(MAKE) verify-db
	CHECK=v020-project-hard-delete $(MAKE) verify-db
	CHECK=v020-document-health-fields $(MAKE) verify-db
	CHECK=v020-document-hard-delete $(MAKE) verify-db
	CHECK=v020-delete-consistency $(MAKE) verify-db
	CHECK=v020-delete-trash-cleanup $(MAKE) verify-db
	CHECK=v020-document-reprocess-no-duplicates $(MAKE) verify-db
	CHECK=v020-processing-failure-fields $(MAKE) verify-db
	CHECK=v020-processing-embedding-failure-stage $(MAKE) verify-db
	CHECK=v020-source-detail-fields $(MAKE) verify-db
	CHECK=v020-question-research-consistency $(MAKE) verify-db
	CHECK=v020-reprocess-research-consistency $(MAKE) verify-db

v020-api-test:
	CHECK=v020-project-document-api $(MAKE) verify-api-contract
	CHECK=v020-document-detail-fields $(MAKE) verify-api-contract
	CHECK=v020-document-reprocess-api $(MAKE) verify-api-contract
	CHECK=v020-delete-api $(MAKE) verify-api-contract
	CHECK=v020-document-scope-disabled $(MAKE) verify-api-contract
	CHECK=v020-pdf-file-api $(MAKE) verify-api-contract
	CHECK=v020-project-name-limits $(MAKE) verify-api-contract
	CHECK=v020-question-scope-errors $(MAKE) verify-api-contract
	CHECK=v020-question-history-api $(MAKE) verify-api-contract
	CHECK=v020-question-detail-api $(MAKE) verify-api-contract
	CHECK=v020-question-research-scope-errors $(MAKE) verify-api-contract
	CHECK=v020-question-embedding-failure-api $(MAKE) verify-api-contract
	CHECK=v020-question-api $(MAKE) verify-api-contract
	CHECK=v020-stale-source $(MAKE) verify-api-contract
	CHECK=v020-model-api $(MAKE) verify-api-contract
