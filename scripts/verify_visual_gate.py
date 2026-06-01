from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "tmp/v0.2.0-visual-evidence"
MANIFEST_PATH = EVIDENCE_DIR / "manifest.json"
VISUAL_AUDIT_PATH = REPO_ROOT / "docs/spec/v0.2.0/visual-audit.md"

VALID_STATES = {
    "first-empty-project",
    "project-created",
    "document-list",
    "document-health",
    "paper-ingest-uploading",
    "processing-rail-running",
    "processing-failure-actions",
    "question-search",
    "source-confidence-levels",
    "no-reliable-source",
    "focus-mode",
    "source-detail",
    "source-page-nav",
    "pdf-reader",
    "long-lists",
    "mobile-workspace",
}
VALID_VIEWPORTS = {"1440x900", "1280x832", "1200x800", "1024x768", "390x844"}
SCREENSHOT_FIELDS = {"state", "viewport", "path", "url", "browser", "data_command", "captured_at"}
AUDIT_HEADINGS = [
    "## 审计元信息",
    "## 截图矩阵结论",
    "## 问题列表",
    "## 修复记录",
    "## 最终结论",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_utc_iso(value: Any, field: str) -> None:
    require(isinstance(value, str), f"{field} must be string")
    require(value.endswith("Z"), f"{field} must use UTC Z suffix")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise SystemExit(f"{field} must be ISO-8601 UTC: {value}") from exc


def verify_manifest() -> None:
    require(MANIFEST_PATH.exists(), f"visual evidence manifest missing: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"visual evidence manifest is not valid JSON: {exc}") from exc

    require(isinstance(manifest, dict), "visual evidence manifest must be a JSON object")
    require(manifest.get("version") == "v0.2.0", "manifest.version must be v0.2.0")
    git_commit = manifest.get("git_commit")
    require(isinstance(git_commit, str) and re.fullmatch(r"[0-9a-f]{40}", git_commit) is not None, "manifest.git_commit must be a 40 character lowercase SHA")
    require_utc_iso(manifest.get("generated_at"), "manifest.generated_at")

    screenshots = manifest.get("screenshots")
    require(isinstance(screenshots, list), "manifest.screenshots must be an array")
    require(len(screenshots) > 0, "manifest.screenshots must not be empty")
    seen: set[tuple[str, str]] = set()
    for index, screenshot in enumerate(screenshots):
        require(isinstance(screenshot, dict), f"screenshots[{index}] must be an object")
        require(set(screenshot) == SCREENSHOT_FIELDS, f"screenshots[{index}] fields mismatch: {sorted(screenshot)}")
        state = screenshot["state"]
        viewport = screenshot["viewport"]
        require(state in VALID_STATES, f"screenshots[{index}].state unsupported: {state}")
        require(viewport in VALID_VIEWPORTS, f"screenshots[{index}].viewport unsupported: {viewport}")
        key = (state, viewport)
        require(key not in seen, f"duplicate screenshot entry: {state} {viewport}")
        seen.add(key)
        path = screenshot["path"]
        require(isinstance(path, str) and path.endswith(".png"), f"screenshots[{index}].path must be a PNG path")
        screenshot_path = (REPO_ROOT / path).resolve()
        require(screenshot_path.is_relative_to(REPO_ROOT), f"screenshots[{index}].path escapes repo: {path}")
        require(screenshot_path.is_relative_to(EVIDENCE_DIR), f"screenshots[{index}].path must be under tmp/v0.2.0-visual-evidence: {path}")
        require(screenshot_path.name == f"{viewport}-{state}.png", f"screenshots[{index}].path must be named {viewport}-{state}.png")
        require(screenshot_path.exists(), f"screenshots[{index}].path does not exist: {path}")
        require(screenshot_path.stat().st_size > 1000, f"screenshots[{index}].path is too small: {path}")
        require(isinstance(screenshot["url"], str) and screenshot["url"].startswith("http://"), f"screenshots[{index}].url must be local http URL")
        require(isinstance(screenshot["browser"], str) and screenshot["browser"], f"screenshots[{index}].browser must be non-empty")
        require(isinstance(screenshot["data_command"], str) and screenshot["data_command"], f"screenshots[{index}].data_command must be non-empty")
        require_utc_iso(screenshot["captured_at"], f"screenshots[{index}].captured_at")
    states = {state for state, _ in seen}
    viewports = {viewport for _, viewport in seen}
    require(states == VALID_STATES, f"manifest.screenshots must cover every state: missing={sorted(VALID_STATES - states)} extra={sorted(states - VALID_STATES)}")
    require(
        viewports == VALID_VIEWPORTS,
        f"manifest.screenshots must cover every viewport: missing={sorted(VALID_VIEWPORTS - viewports)} extra={sorted(viewports - VALID_VIEWPORTS)}",
    )


def verify_aesthetic_audit_record() -> None:
    require(VISUAL_AUDIT_PATH.exists(), f"visual audit record missing: {VISUAL_AUDIT_PATH.relative_to(REPO_ROOT)}")
    content = VISUAL_AUDIT_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    require(lines[:1] == ["# Suton v0.2.0 视觉审计记录"], "visual audit title mismatch")
    positions = []
    for heading in AUDIT_HEADINGS:
        try:
            positions.append(lines.index(heading))
        except ValueError as exc:
            raise SystemExit(f"visual audit missing heading: {heading}") from exc
    require(positions == sorted(positions), "visual audit headings are out of order")
    final_index = positions[-1]
    require(final_index + 1 < len(lines), "visual audit final conclusion missing")
    require(lines[final_index + 1] == "结论：通过", "visual audit final conclusion must be: 结论：通过")


def main() -> None:
    check = os.getenv("CHECK", "visual-evidence-manifest")
    if check == "visual-evidence-manifest":
        verify_manifest()
    elif check == "aesthetic-audit-record":
        verify_aesthetic_audit_record()
    else:
        raise SystemExit(f"unsupported CHECK={check}")
    print(f"CHECK={check} passed")


if __name__ == "__main__":
    main()
