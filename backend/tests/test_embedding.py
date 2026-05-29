from __future__ import annotations

import pytest
from types import SimpleNamespace

from app import embedding


class _FakeEmbedding:
    def __init__(self, values: list[float]) -> None:
        self.embedding = values


class _FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    def create(self, *, model: str, input: list[str], encoding_format: str):
        assert model == "text-embedding-v4"
        assert encoding_format == "float"
        self.batch_sizes.append(len(input))
        return type("EmbeddingResponse", (), {"data": [_FakeEmbedding([0.1] * 1024) for _ in input]})()


class _FakeClient:
    resource = _FakeEmbeddingsResource()

    def __init__(self, *, api_key: str, base_url: str) -> None:
        assert api_key == "test-key"
        assert base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.embeddings = self.resource


def test_embed_texts_batches_dashscope_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeClient.resource = _FakeEmbeddingsResource()
    monkeypatch.setattr(
        embedding,
        "settings",
        SimpleNamespace(
            dashscope_api_key="test-key",
            dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            embedding_model="text-embedding-v4",
            embedding_dimension=1024,
        ),
    )
    monkeypatch.setattr(embedding, "OpenAI", _FakeClient)

    vectors = embedding.embed_texts([f"text-{index}" for index in range(23)])

    assert len(vectors) == 23
    assert _FakeClient.resource.batch_sizes == [10, 10, 3]


def test_embed_texts_rejects_wrong_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    class WrongDimensionResource:
        def create(self, *, model: str, input: list[str], encoding_format: str):
            return type("EmbeddingResponse", (), {"data": [_FakeEmbedding([0.1] * 3)]})()

    class WrongDimensionClient:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            self.embeddings = WrongDimensionResource()

    monkeypatch.setattr(
        embedding,
        "settings",
        SimpleNamespace(
            dashscope_api_key="test-key",
            dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            embedding_model="text-embedding-v4",
            embedding_dimension=1024,
        ),
    )
    monkeypatch.setattr(embedding, "OpenAI", WrongDimensionClient)

    with pytest.raises(embedding.EmbeddingConfigurationError, match="embedding 维度"):
        embedding.embed_texts(["text"])
