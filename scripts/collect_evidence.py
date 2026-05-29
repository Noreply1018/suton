from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMMANDS = [
    ["git", "status", "--short", "--branch"],
    ["git", "rev-parse", "HEAD"],
    ["git", "ls-remote", "--heads", "origin", "main"],
    ["make", "env-info"],
    ["make", "verify-spec"],
    ["make", "verify-secrets"],
]
TEST_COMMAND = ["make", "test"]
SECRET_REPLACEMENTS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)(\s*[:=]\s*)['\"]?[^'\"\s]+"),
]


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_REPLACEMENTS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>" if match.lastindex == 2 else "<redacted>", redacted)
    return redacted


def run_command(command: list[str], timeout: int) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=os.environ.copy(),
    )
    return result.returncode, redact(result.stdout.strip())


def render_command(command: list[str], returncode: int, output: str) -> str:
    body = output if output else "<no output>"
    return "\n".join(
        [
            f"### `{' '.join(command)}`",
            "",
            f"- exit: `{returncode}`",
            "",
            "```text",
            body,
            "```",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a redacted v0.1.0 validation evidence package.")
    parser.add_argument("--output", default="tmp/v0.1.0-evidence-latest.md", help="Markdown output path.")
    parser.add_argument("--with-tests", action="store_true", help="Include make test in the evidence package.")
    parser.add_argument("--timeout", type=int, default=180, help="Per-command timeout in seconds.")
    args = parser.parse_args()

    commands = [*DEFAULT_COMMANDS]
    if args.with_tests:
        commands.append(TEST_COMMAND)

    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    sections = [
        "# Suton v0.1.0 证据包",
        "",
        f"- 生成时间：`{now}`",
        "- 脱敏规则：API key、token、secret、password 类值统一替换为 `<redacted>`。",
        "",
    ]
    failed: list[str] = []
    for command in commands:
        try:
            returncode, output = run_command(command, args.timeout)
        except subprocess.TimeoutExpired:
            returncode, output = 124, f"command timed out after {args.timeout}s"
        sections.append(render_command(command, returncode, output))
        if returncode != 0:
            failed.append(" ".join(command))

    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections), encoding="utf-8")
    try:
        display_path = output_path.relative_to(ROOT)
    except ValueError:
        display_path = output_path
    print(f"wrote evidence package: {display_path}")
    if failed:
        raise SystemExit(f"evidence commands failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
