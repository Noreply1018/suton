from __future__ import annotations

from pathlib import Path
import time

from app.db import connect


def main() -> None:
    sql = Path("backend/app/schema.sql").read_text(encoding="utf-8")
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with connect() as conn:
                conn.execute(sql)
                conn.commit()
            print("schema-v0.1.0 migrated")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1)
    raise SystemExit(f"database not ready: {last_error}")


if __name__ == "__main__":
    main()
