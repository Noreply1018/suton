from __future__ import annotations

from openai import OpenAI

from app.config import settings


class EmbeddingConfigurationError(RuntimeError):
    pass


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.dashscope_api_key:
        raise EmbeddingConfigurationError("缺少 DASHSCOPE_API_KEY，无法生成 Suton 要求的 DashScope embedding")
    client = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 10):
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=texts[start : start + 10],
            encoding_format="float",
        )
        vectors.extend(item.embedding for item in response.data)
    for vector in vectors:
        if len(vector) != settings.embedding_dimension:
            raise EmbeddingConfigurationError(
                f"embedding 维度为 {len(vector)}，不等于 {settings.embedding_dimension}"
            )
    return vectors
