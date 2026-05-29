from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://suton:suton@localhost:54329/suton")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:56379/0")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    dashscope_api_key: str | None = os.getenv("DASHSCOPE_API_KEY")
    dashscope_base_url: str = os.getenv("DASH_SCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "dashscope")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))


settings = Settings()
