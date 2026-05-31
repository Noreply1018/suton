from __future__ import annotations


def rq_import_check() -> dict[str, str | int]:
    from app.config import settings
    from app.processing import process_document

    return {
        "processing_entrypoint": process_document.__name__,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "database_url": "set" if settings.database_url else "missing",
        "redis_url": "set" if settings.redis_url else "missing",
        "dashscope_api_key": "set" if settings.dashscope_api_key else "missing",
    }
