from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs/spec/v0.1.0"
ITEMS_DIR = SPEC_DIR / "items"
VALIDATION_DOC = SPEC_DIR / "validation-2026-05-29.md"
V020_SPEC_DIR = ROOT / "docs/spec/v0.2.0"
V020_ITEMS_DIR = V020_SPEC_DIR / "items"


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


def check_item(path: Path, *, completed: bool) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if "- 状态：" not in text:
        errors.append(f"{path}: 缺少状态字段")
    rows = table_rows(text)
    if not rows:
        errors.append(f"{path}: 缺少验证矩阵行")
        return errors
    for index, row in enumerate(rows, start=1):
        if len(row) != 8:
            errors.append(f"{path}: 验证矩阵第 {index} 行列数不是 8")
            continue
        scenario, environment, precondition, command, expected, actual, evidence, conclusion = row
        if completed and conclusion != "通过":
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


REQUIRED_ITEM_FIELDS = [
    "- 类型：",
    "- 状态：",
    "- 背景：",
    "- 当前问题：",
    "- 目标行为：",
    "- 非目标：",
    "- 发布必要性：",
    "- 用户可见影响：",
    "- 涉及模块：",
    "- 配置、接口或数据结构变化：",
    "- 兼容性要求：",
    "- 验收标准：",
    "- 验证矩阵：",
    "- 风险与回滚：",
]


def check_v020_item(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for field in REQUIRED_ITEM_FIELDS:
        if field not in text:
            errors.append(f"{path}: 缺少字段 {field}")
    if "- 发布必要性：必须发布" not in text:
        errors.append(f"{path}: 发布必要性必须为“必须发布”")
    rows = table_rows(text)
    if not rows:
        errors.append(f"{path}: 缺少验证矩阵行")
        return errors
    for index, row in enumerate(rows, start=1):
        if len(row) != 8:
            errors.append(f"{path}: 验证矩阵第 {index} 行列数不是 8")
            continue
        scenario, environment, precondition, command, expected, actual, evidence, conclusion = row
        for label, value in {
            "场景": scenario,
            "环境": environment,
            "前置条件": precondition,
            "操作命令": command,
            "预期结果": expected,
            "实际结果": actual,
            "证据": evidence,
            "结论": conclusion,
        }.items():
            if not value:
                errors.append(f"{path}: 验证矩阵第 {index} 行缺少{label}")
        if "执行 v0.2.0" in command or "命令" == command:
            errors.append(f"{path}: 场景“{scenario}”操作命令不是可复现命令")
        if conclusion not in {"通过", "失败", "阻塞", "移除"}:
            errors.append(f"{path}: 场景“{scenario}”结论非法：{conclusion}")
    return errors


def check_v020_spec() -> list[str]:
    errors: list[str] = []
    required_files = [
        V020_SPEC_DIR / "README.md",
        V020_SPEC_DIR / "acceptance-checklist.md",
        V020_ITEMS_DIR / "design-001-frontend-rebuild.md",
        V020_ITEMS_DIR / "design-002-workspace-layout.md",
        V020_ITEMS_DIR / "feature-001-project-management.md",
        V020_ITEMS_DIR / "feature-002-document-management.md",
        V020_ITEMS_DIR / "feature-003-processing-progress.md",
        V020_ITEMS_DIR / "feature-004-source-reader.md",
        V020_ITEMS_DIR / "feature-005-question-workflow.md",
        V020_ITEMS_DIR / "data-001-v020-model-api.md",
        V020_ITEMS_DIR / "gate-001-visual-quality.md",
        V020_ITEMS_DIR / "gate-002-v020-validation.md",
    ]
    for path in required_files:
        if not path.exists():
            errors.append(f"missing v0.2.0 spec file: {path}")
    if errors:
        return errors

    readme = (V020_SPEC_DIR / "README.md").read_text(encoding="utf-8")
    required_readme_text = [
        "Nature 论文式高级浅色自然系",
        "旧前端实现内容必须被替换",
        "成熟产品",
        "不得复制任何特定产品",
        "tests/fixtures/text-layer-material.pdf",
        "tests/fixtures/unmatched-question.txt",
        "前端旧设计已彻底删除",
    ]
    for required in required_readme_text:
        if required not in readme:
            errors.append(f"{V020_SPEC_DIR / 'README.md'}: 缺少关键约束 {required}")

    for path in sorted(V020_ITEMS_DIR.glob("*.md")):
        errors.extend(check_v020_item(path))
    return errors


def main() -> None:
    require(SPEC_DIR.exists(), f"spec directory not found: {SPEC_DIR}")
    require(VALIDATION_DOC.exists(), f"validation document not found: {VALIDATION_DOC}")
    item_paths = sorted(ITEMS_DIR.glob("*.md"))
    require(item_paths, f"spec item files not found: {ITEMS_DIR}")

    errors: list[str] = []
    incomplete_items: list[str] = []
    for path in item_paths:
        text = path.read_text(encoding="utf-8")
        completed = "- 状态：已完成" in text
        if not completed:
            incomplete_items.append(str(path.relative_to(ROOT)))
        errors.extend(check_item(path, completed=completed))

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
    if incomplete_items:
        fail("v0.1.0 release blocked by incomplete spec items:\n" + "\n".join(incomplete_items))

    v020_errors = check_v020_spec()
    if v020_errors:
        fail("\n".join(v020_errors))

    print("v0.1.0 release gate spec checks passed")
    print("v0.2.0 draft spec structure checks passed")


if __name__ == "__main__":
    main()
