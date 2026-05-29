from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {
    ".css",
    ".env",
    ".example",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
OPENAI_LIKE_API_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")
DASHSCOPE_API_KEY = re.compile(r"\bsk-[A-Za-z0-9]{24,}\b")
GENERIC_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?(?P<value>[A-Za-z0-9_./+=()\"'-]{16,})"
)
GENERIC_VALUE_ALLOWLIST_PREFIXES = (
    "settings.",
    "os.getenv",
    "getenv(",
    "os.environ",
    "config.",
    "<",
    "your_",
    "placeholder",
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.name in {".env.example", "Makefile", "AGENTS.md", "README.md"}


def is_allowed_generic_value(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return any(normalized.startswith(prefix) for prefix in GENERIC_VALUE_ALLOWLIST_PREFIXES)


def scan_text(text: str, rel_path: str) -> list[str]:
    findings: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if OPENAI_LIKE_API_KEY.search(line):
            findings.append(f"{rel_path}:{line_no}: possible openai-like-api-key")
        if DASHSCOPE_API_KEY.search(line):
            findings.append(f"{rel_path}:{line_no}: possible dashscope-api-key")
        for match in GENERIC_SECRET_ASSIGNMENT.finditer(line):
            if is_allowed_generic_value(match.group("value")):
                continue
            findings.append(f"{rel_path}:{line_no}: possible generic-secret-assignment")
    return findings


def main() -> None:
    findings: list[str] = []
    for path in tracked_files():
        if not path.exists() or not is_text_candidate(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_path = os.fspath(path.relative_to(ROOT))
        findings.extend(scan_text(text, rel_path))
    if findings:
        raise SystemExit("\n".join(findings))
    print("tracked-file secret scan passed")


if __name__ == "__main__":
    main()
