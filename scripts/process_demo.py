from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.db import connect
from app.processing import create_uploaded_document, process_document


def ensure_project() -> int:
    with connect() as conn:
        project = conn.execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()
        if project:
            return project["id"]
        row = conn.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", ("高等数学（上）期末复习",)).fetchone()
        conn.commit()
        return row["id"]


def main() -> None:
    file_arg = os.getenv("FILE", "tests/fixtures/text-layer-material.pdf")
    source = Path(file_arg)
    if not source.exists():
        raise SystemExit(f"fixture not found: {source}")
    project_id = ensure_project()
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"project-{project_id}-{source.name}"
    shutil.copyfile(source, target)
    document_id = create_uploaded_document(project_id, source.name, "application/pdf", str(target))
    try:
        process_document(document_id)
    except Exception:
        if os.getenv("EXPECT_FAILURE") or os.getenv("EXPECT_UNSUPPORTED"):
            print(f"document {document_id} failed as expected")
            return
        raise
    with connect() as conn:
        document = conn.execute("SELECT status FROM documents WHERE id = %s", (document_id,)).fetchone()
    if os.getenv("EXPECT_UNSUPPORTED"):
        if document["status"] == "unsupported":
            print(f"document {document_id} unsupported as expected")
            return
        raise SystemExit(f"expected unsupported but status is {document['status']}")
    if os.getenv("EXPECT_FAILURE"):
        if document["status"] == "failed":
            print(f"document {document_id} failed as expected")
            return
        raise SystemExit(f"expected failure but status is {document['status']}")
    print(f"document {document_id} processed")


if __name__ == "__main__":
    main()
