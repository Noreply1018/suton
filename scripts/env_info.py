from __future__ import annotations

import os
import shutil
import subprocess
import sys

from app.config import settings


def command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return result.stdout.strip() or result.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return f"missing-or-failed: {exc}"


def binary_version(binary: str, args: list[str]) -> str:
    path = shutil.which(binary)
    if not path:
        return "missing"
    return command_output([binary, *args])


def main() -> None:
    print(f"Node.js: {binary_version('node', ['--version'])}")
    print(f"pnpm: {binary_version('pnpm', ['--version'])}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"uv: {binary_version('uv', ['--version'])}")
    print(f"Docker: {binary_version('docker', ['--version'])}")
    print(f"PostgreSQL: docker compose service postgres / pgvector image pgvector/pgvector:pg16")
    print(f"pgvector: required by backend/app/schema.sql CREATE EXTENSION vector")
    print(f"Redis: docker compose service redis:7-alpine")
    print(f"RQ: {binary_version('uv', ['run', '--project', 'backend', 'python', '-c', 'import rq; print(rq.__version__)'])}")
    print(f"embedding provider: {settings.embedding_provider}")
    print(f"embedding model: {settings.embedding_model}")
    print(f"embedding dimension: {settings.embedding_dimension}")
    print(f"DashScope Base URL: {settings.dashscope_base_url}")
    print(f"DASHSCOPE_API_KEY exists: {'yes' if os.getenv('DASHSCOPE_API_KEY') else 'no'}")
    print(f"DATABASE_URL exists: {'yes' if os.getenv('DATABASE_URL') else 'default'}")
    print(f"REDIS_URL exists: {'yes' if os.getenv('REDIS_URL') else 'default'}")
    print(f"UPLOAD_DIR: {settings.upload_dir}")
    print(f"Playwright browsers: {binary_version('pnpm', ['exec', 'playwright', '--version'])}")
    print(f"OS: {command_output(['uname', '-a'])}")


if __name__ == "__main__":
    main()
