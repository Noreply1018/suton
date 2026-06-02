from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V010_COMMANDS = [
    ["git", "status", "--short", "--branch"],
    ["git", "rev-parse", "HEAD"],
    ["git", "ls-remote", "--heads", "origin", "main"],
    ["make", "env-info"],
    ["make", "verify-spec"],
    ["make", "verify-secrets"],
]
TEST_COMMAND = ["make", "test"]
V020_COMMANDS = [
    {"command": ["git", "status", "--short", "--branch"], "data": "git worktree state", "evidence": "local git status"},
    {"command": ["git", "rev-parse", "HEAD"], "data": "git commit", "evidence": "local git HEAD"},
    {"command": ["make", "env-info"], "data": "local environment inspection", "evidence": "command output"},
    {"command": ["make", "reset-demo"], "data": "reset demo database and files", "evidence": "command output"},
    {"command": ["make", "migrate"], "data": "PostgreSQL migration", "evidence": "command output"},
    {
        "command": ["make", "verify-e2e", "SCENARIO=v020-full-regression"],
        "data": "full v0.2.0 browser regression",
        "evidence": "Playwright output",
    },
    {
        "command": ["make", "verify-api-contract", "CHECK=v020-model-api"],
        "data": "v0.2.0 API contract fixtures",
        "evidence": "command output",
    },
    {"command": ["make", "verify-db", "CHECK=v020-schema"], "data": "v0.2.0 schema inspection", "evidence": "command output"},
    {
        "command": ["make", "verify-visual", "CHECK=screenshot-matrix"],
        "data": "fixed visual seed matrix",
        "evidence": "tmp/v0.2.0-visual-evidence/",
    },
    {
        "command": ["make", "verify-visual", "CHECK=visual-hard-errors"],
        "data": "fixed viewport visual hard error seed",
        "evidence": "Playwright DOM checks",
    },
    {
        "command": ["make", "verify-visual", "CHECK=visual-evidence-manifest"],
        "data": "generated visual manifest",
        "evidence": "tmp/v0.2.0-visual-evidence/manifest.json",
    },
    {
        "command": ["make", "verify-visual", "CHECK=aesthetic-audit-record"],
        "data": "subagent visual audit record",
        "evidence": "docs/spec/v0.2.0/visual-audit.md",
    },
    {"command": TEST_COMMAND, "data": "backend, frontend, v0.2.0 DB/API test suite", "evidence": "command output"},
    {"command": ["make", "verify-spec"], "data": "spec structure and release gate checks", "evidence": "command output"},
    {"command": ["make", "verify-secrets"], "data": "tracked-file secret scan", "evidence": "command output"},
]
SECRET_REPLACEMENTS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)(\s*[:=]\s*)['\"]?[^'\"\s]+"),
    re.compile(r"(?im)^(authorization|cookie)(\s*:\s*).+$"),
]


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_REPLACEMENTS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>" if match.lastindex == 2 else "<redacted>", redacted)
    return redacted


def run_command(command: list[str], timeout: int) -> tuple[int, str, float]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=os.environ.copy(),
    )
    duration = time.monotonic() - started
    return result.returncode, redact(result.stdout.strip()), duration


def render_command(command: list[str], returncode: int, output: str, duration: float | None = None, data: str | None = None, evidence: str | None = None) -> str:
    body = output if output else "<no output>"
    conclusion = "通过" if returncode == 0 else "失败"
    lines = [
        f"### `{' '.join(command)}`",
        "",
        f"- exit: `{returncode}`",
        f"- 结论：{conclusion}",
    ]
    if duration is not None:
        lines.append(f"- 执行时间：`{duration:.2f}s`")
    if data:
        lines.append(f"- 数据准备命令：{data}")
    if evidence:
        lines.append(f"- 证据路径：{evidence}")
    lines.extend(["", "```text", body, "```", ""])
    return "\n".join(lines)


def visual_evidence_summary() -> list[str]:
    evidence_dir = ROOT / "tmp/v0.2.0-visual-evidence"
    manifest_path = evidence_dir / "manifest.json"
    visual_audit_path = ROOT / "docs/spec/v0.2.0/visual-audit.md"
    lines = ["## v0.2.0 视觉证据", ""]
    lines.append(f"- 截图目录：`{evidence_dir.relative_to(ROOT)}`，存在：`{evidence_dir.exists()}`。")
    lines.append(f"- manifest：`{manifest_path.relative_to(ROOT)}`，存在：`{manifest_path.exists()}`。")
    if manifest_path.exists():
        try:
            import json

            manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
            screenshots = manifest.get("screenshots", [])
            if isinstance(screenshots, list):
                states = sorted({item.get("state") for item in screenshots if isinstance(item, dict)})
                viewports = sorted({item.get("viewport") for item in screenshots if isinstance(item, dict)})
                lines.append(f"- manifest 版本：`{manifest.get('version')}`。")
                lines.append(f"- manifest Git commit：`{manifest.get('git_commit')}`。")
                lines.append(f"- 截图数量：`{len(screenshots)}`；状态数：`{len(states)}`；viewport 数：`{len(viewports)}`。")
                lines.append(f"- 状态集合：`{', '.join(str(item) for item in states)}`。")
                lines.append(f"- viewport 集合：`{', '.join(str(item) for item in viewports)}`。")
        except Exception as exc:  # pragma: no cover - evidence rendering must not hide command results
            lines.append(f"- manifest 读取失败：`{type(exc).__name__}: {exc}`。")
    lines.append(f"- 人工审美审计：`{visual_audit_path.relative_to(ROOT)}`，存在：`{visual_audit_path.exists()}`。")
    if visual_audit_path.exists():
        audit_lines = visual_audit_path.read_text(encoding="utf-8").splitlines()
        try:
            final_index = audit_lines.index("## 最终结论")
            final_conclusion = audit_lines[final_index + 1] if final_index + 1 < len(audit_lines) else "<missing>"
        except ValueError:
            final_conclusion = "<missing heading>"
        lines.append(f"- 人工审美审计最终结论：`{final_conclusion}`。")
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a redacted validation evidence package.")
    parser.add_argument("--version", choices=["v0.1.0", "v0.2.0"], default="v0.1.0", help="Evidence package version.")
    parser.add_argument("--output", help="Markdown output path.")
    parser.add_argument("--with-tests", action="store_true", help="Include make test in the evidence package.")
    parser.add_argument("--timeout", type=int, default=180, help="Per-command timeout in seconds.")
    args = parser.parse_args()

    if args.version == "v0.2.0":
        command_specs = V020_COMMANDS if args.with_tests else [item for item in V020_COMMANDS if item["command"] != TEST_COMMAND]
        default_output = "tmp/v0.2.0-evidence-latest.md"
    else:
        commands = [*V010_COMMANDS]
        if args.with_tests:
            commands.append(TEST_COMMAND)
        command_specs = [{"command": command, "data": None, "evidence": None} for command in commands]
        default_output = "tmp/v0.1.0-evidence-latest.md"

    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    sections = [
        f"# Suton {args.version} 证据包",
        "",
        f"- 生成时间：`{now}`",
        "- 脱敏规则：API key、token、secret、password 类值统一替换为 `<redacted>`。",
        "",
    ]
    if args.version == "v0.2.0":
        sections.extend(visual_evidence_summary())
    failed: list[str] = []
    for spec in command_specs:
        command = spec["command"]
        try:
            returncode, output, duration = run_command(command, args.timeout)
        except subprocess.TimeoutExpired:
            returncode, output, duration = 124, f"command timed out after {args.timeout}s", float(args.timeout)
        sections.append(render_command(command, returncode, output, duration, spec.get("data"), spec.get("evidence")))
        if returncode != 0:
            failed.append(" ".join(command))

    output_path = (ROOT / (args.output or default_output)).resolve()
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
