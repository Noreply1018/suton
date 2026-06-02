from __future__ import annotations

import shutil
from pathlib import Path

from redis import Redis
from rq import Queue
from rq.registry import (
    CanceledJobRegistry,
    DeferredJobRegistry,
    FailedJobRegistry,
    FinishedJobRegistry,
    ScheduledJobRegistry,
    StartedJobRegistry,
)

from app.config import settings
from app.db import connect


def clear_processing_queue() -> None:
    connection = Redis.from_url(settings.redis_url)
    queue = Queue("suton", connection=connection)
    queue.empty()
    for registry_type in (
        StartedJobRegistry,
        DeferredJobRegistry,
        FailedJobRegistry,
        FinishedJobRegistry,
        ScheduledJobRegistry,
        CanceledJobRegistry,
    ):
        registry = registry_type(queue=queue)
        for job_id in registry.get_job_ids():
            registry.remove(job_id, delete_job=True)


def main() -> None:
    schema = Path("backend/app/schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.execute(schema)
        conn.execute("TRUNCATE question_matches, questions, chunks, document_pages, documents, projects RESTART IDENTITY CASCADE")
        conn.commit()
    clear_processing_queue()
    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    print("demo state reset")


if __name__ == "__main__":
    main()
