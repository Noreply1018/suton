from __future__ import annotations

from pathlib import Path
import time

from app.db import connect


def migrated_project_name(project_id: int, raw_name: str | None, used: set[str]) -> str:
    base = (raw_name or "").strip()
    if not base:
        base = f"迁移项目 {project_id}"
    base = base[:80]
    candidate = base
    if candidate in used:
        n = 2
        while True:
            suffix = f"（迁移 {n}）"
            candidate = base[: 80 - len(suffix)] + suffix
            if candidate not in used:
                break
            n += 1
    used.add(candidate)
    return candidate


def normalize_project_names() -> None:
    with connect() as conn:
        rows = conn.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
        used: set[str] = set()
        updates: list[tuple[str, int]] = []
        for row in rows:
            project_id = int(row["id"])
            candidate = migrated_project_name(project_id, row["name"], used)
            if candidate != row["name"]:
                updates.append((candidate, project_id))
        for name, project_id in updates:
            conn.execute("UPDATE projects SET name = %s WHERE id = %s", (name, project_id))
        conn.execute("ALTER TABLE projects ALTER COLUMN name SET NOT NULL")
        conn.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_name_check")
        conn.execute("ALTER TABLE projects ADD CONSTRAINT projects_name_check CHECK (length(btrim(name)) > 0 AND length(name) <= 80 AND name = btrim(name))")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS projects_workspace_name_unique ON projects (workspace_id, name)")
        conn.commit()


def normalize_chunk_offsets() -> None:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.page_id, c.text, p.normalized_text
            FROM chunks c
            JOIN document_pages p ON p.id = c.page_id
            ORDER BY c.page_id, c.id
            """
        ).fetchall()
        search_from_by_page: dict[int, int] = {}
        updates: list[tuple[int, int, int]] = []
        for row in rows:
            page_id = int(row["page_id"])
            text = row["text"]
            normalized_text = row["normalized_text"]
            search_from = search_from_by_page.get(page_id, 0)
            start = normalized_text.find(text, search_from)
            if start < 0:
                start = normalized_text.find(text)
            if start < 0:
                continue
            end = start + len(text)
            search_from_by_page[page_id] = end
            updates.append((start, end, int(row["id"])))
        for start, end, chunk_id in updates:
            conn.execute(
                "UPDATE chunks SET page_start_char = %s, page_end_char = %s WHERE id = %s",
                (start, end, chunk_id),
            )
        conn.commit()


def main() -> None:
    sql = Path("backend/app/schema.sql").read_text(encoding="utf-8")
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with connect() as conn:
                conn.execute(sql)
                conn.commit()
            normalize_chunk_offsets()
            normalize_project_names()
            print("schema migrated")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1)
    raise SystemExit(f"database not ready: {last_error}")


if __name__ == "__main__":
    main()
