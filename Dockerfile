# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS frontend-builder

ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /web
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/package.json
RUN pnpm install --frozen-lockfile
COPY frontend frontend
RUN pnpm --filter @suton/web build

FROM python:3.12-slim AS runtime

ARG SUTON_VERSION=dev
ARG SUTON_COMMIT=unknown
ARG SUTON_BUILD_DATE=unknown

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend
ENV NEXT_TELEMETRY_DISABLED=1
ENV SUTON_VERSION=${SUTON_VERSION}
ENV SUTON_COMMIT=${SUTON_COMMIT}
ENV SUTON_BUILD_DATE=${SUTON_BUILD_DATE}
ENV DATABASE_URL=postgresql://suton:suton@postgres:5432/suton
ENV REDIS_URL=redis://redis:6379/0
ENV UPLOAD_DIR=/app/uploads
ENV DASH_SCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ENV EMBEDDING_PROVIDER=dashscope
ENV EMBEDDING_MODEL=text-embedding-v4
ENV EMBEDDING_DIMENSION=1024
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend --locked

COPY backend/app backend/app
COPY scripts/migrate.py scripts/migrate.py
COPY docker/entrypoint.sh /usr/local/bin/suton-entrypoint
COPY --from=frontend-builder /web/frontend/.next/standalone /app/frontend
COPY --from=frontend-builder /web/frontend/.next/static /app/frontend/frontend/.next/static

RUN chmod +x /usr/local/bin/suton-entrypoint \
    && mkdir -p /app/uploads

EXPOSE 3000 8000
VOLUME ["/app/uploads"]

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=30s \
  CMD curl -fsS http://127.0.0.1:8000/health >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "suton-entrypoint"]
CMD ["up"]
