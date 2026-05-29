from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs/spec/v0.1.0"
ITEMS_DIR = SPEC_DIR / "items"
VALIDATION_DOC = SPEC_DIR / "validation-2026-05-29.md"


def fail(message: str) -> None:
    raise SystemExit(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def table_rows(markdown: str) -> list[list[str]]:
    rows: list[list[str]] = []
    in_matrix = False
    for line in markdown.splitlines():
        if line.strip() == "- 验证矩阵：":
            in_matrix = True
            continue
        if not in_matrix:
            continue
        stripped = line.strip()
        if not stripped:
            if rows:
                break
            continue
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    if rows and rows[0] and rows[0][0] == "场景":
        return rows[1:]
    return rows


def check_item(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if "- 状态：已完成" not in text:
        errors.append(f"{path}: 状态不是已完成")
    rows = table_rows(text)
    if not rows:
        errors.append(f"{path}: 缺少验证矩阵行")
        return errors
    for index, row in enumerate(rows, start=1):
        if len(row) != 8:
            errors.append(f"{path}: 验证矩阵第 {index} 行列数不是 8")
            continue
        scenario, environment, precondition, command, expected, actual, evidence, conclusion = row
        if conclusion != "通过":
            errors.append(f"{path}: 场景“{scenario}”结论不是通过：{conclusion}")
        for label, value in {
            "环境": environment,
            "前置条件": precondition,
            "操作命令": command,
            "预期结果": expected,
            "实际结果": actual,
            "证据": evidence,
        }.items():
            if not value or value in {"-", "无", "待补充", "未验证"}:
                errors.append(f"{path}: 场景“{scenario}”缺少{label}")
        if "docs/spec/v0.1.0/validation-2026-05-29.md" not in evidence:
            errors.append(f"{path}: 场景“{scenario}”证据未引用验证记录")
    return errors


def main() -> None:
    require(SPEC_DIR.exists(), f"spec directory not found: {SPEC_DIR}")
    require(VALIDATION_DOC.exists(), f"validation document not found: {VALIDATION_DOC}")
    item_paths = sorted(ITEMS_DIR.glob("*.md"))
    require(item_paths, f"spec item files not found: {ITEMS_DIR}")

    errors: list[str] = []
    for path in item_paths:
        errors.extend(check_item(path))

    readme = (SPEC_DIR / "README.md").read_text(encoding="utf-8")
    require("远端状态必须在推送后通过 `git ls-remote --heads origin main` 复核" in readme, "README 缺少远端复核规则")
    require("不要求再生成一个只用于记录该输出的新提交" in readme, "README 缺少远端复核非自引用规则")

    validation = VALIDATION_DOC.read_text(encoding="utf-8")
    required_evidence = [
        "make env-info",
        "make test",
        "make verify-e2e",
        "SCENARIO=minimal-loop make verify-e2e",
        "make verify-db CHECK=schema-v0.1.0",
        "make verify-db CHECK=source-lineage",
        "git ls-remote --heads origin main",
    ]
    for evidence in required_evidence:
        if evidence not in validation:
            errors.append(f"{VALIDATION_DOC}: 缺少证据项 {evidence}")

    if errors:
        fail("\n".join(errors))
    print("v0.1.0 release gate spec checks passed")


if __name__ == "__main__":
    main()
