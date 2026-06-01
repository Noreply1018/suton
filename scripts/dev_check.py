from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        print(f"缺少必需工具：{name}", file=sys.stderr)
        sys.exit(1)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-embedding", action="store_true", help="Skip embedding credential preflight for scenarios that do not call embedding.")
    args = parser.parse_args()
    for binary in ("docker", "node", "pnpm", "uv"):
        require_binary(binary)
    if not args.skip_embedding and not os.getenv("DASHSCOPE_API_KEY"):
        print("缺少 DASHSCOPE_API_KEY，无法满足 v0.1.0 embedding 链路", file=sys.stderr)
        sys.exit(1)
    subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL)
    print("dev prerequisites ok")


if __name__ == "__main__":
    main()
