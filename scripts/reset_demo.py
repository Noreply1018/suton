from __future__ import annotations

import shutil
from pathlib import Path

from app.config import settings
from app.db import connect


def main() -> None:
    schema = Path("backend/app/schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.execute(schema)
        conn.execute("TRUNCATE question_matches, questions, chunks, document_pages, documents, projects RESTART IDENTITY CASCADE")
        conn.commit()
    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    print("demo state reset")


if __name__ == "__main__":
    main()
