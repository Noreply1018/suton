from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in values) + "]"
