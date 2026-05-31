# Suton

Suton is a source-first study review web app. Upload a text-layer PDF, paste a question, and get traceable source results with file name, page number, excerpt, pgvector similarity score, hit reason, and a PDF page entry.

## Quick Start

```bash
curl -O https://raw.githubusercontent.com/Noreply1018/suton/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/Noreply1018/suton/main/.env.example
cp .env.example .env
```

Set `DASHSCOPE_API_KEY` in `.env`, then run:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

Open:

```text
http://127.0.0.1:3000
```

Suton v0.1.0 supports text-layer PDFs and manual question input. OCR, automatic question splitting, long AI explanations, knowledge graphs, and APK builds are out of scope.
