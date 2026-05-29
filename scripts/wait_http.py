from __future__ import annotations

import sys
import time
from urllib.request import urlopen


def wait_for(url: str) -> None:
    last_error: Exception | None = None
    for _ in range(120):
        try:
            with urlopen(url, timeout=1) as response:  # noqa: S310 - local dev URLs only
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(1)
    raise SystemExit(f"service not ready: {url}: {last_error}")


def main() -> None:
    for url in sys.argv[1:]:
        wait_for(url)
        print(f"ready: {url}")


if __name__ == "__main__":
    main()
