from __future__ import annotations

import os
from pathlib import Path

from app.db import connect
from app.processing import search_question


def main() -> None:
    question_file = Path(os.getenv("QUESTION", "tests/fixtures/question.txt"))
    text = question_file.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"empty question file: {question_file}")
    with connect() as conn:
        project = conn.execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()
    if not project:
        raise SystemExit("project not found")
    question_id = search_question(project["id"], text)
    print(f"question {question_id} searched")


if __name__ == "__main__":
    main()
