from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs/spec/v0.1.0"
ITEMS_DIR = SPEC_DIR / "items"
VALIDATION_DOC = SPEC_DIR / "validation-2026-05-29.md"
V020_SPEC_DIR = ROOT / "docs/spec/v0.2.0"
V020_ITEMS_DIR = V020_SPEC_DIR / "items"
MAKEFILE = ROOT / "Makefile"
V020_E2E_SPEC = ROOT / "frontend/e2e/v010.spec.ts"
VERIFY_DB = ROOT / "scripts/verify_db.py"
VERIFY_API_CONTRACT = ROOT / "scripts/verify_api_contract.py"
VERIFY_VISUAL_GATE = ROOT / "scripts/verify_visual_gate.py"
DASHSCOPE_REQUIRED_E2E_SCENARIOS = {
    "v020-document-reprocess",
    "v020-document-scope-search",
    "v020-question-search",
    "v020-question-no-source",
    "v020-processing-progress",
    "v020-core-loop",
    "v020-full-regression",
}


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


def extract_python_mapping_keys(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "main":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "checks" for target in child.targets):
                continue
            if not isinstance(child.value, ast.Dict):
                continue
            keys: set[str] = set()
            for key in child.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value.startswith("v020-"):
                    keys.add(key.value)
            return keys
    return set()


def extract_makefile_visual_checks() -> set[str]:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    checks = set(re.findall(r"(?:else )?ifeq \(\$\(CHECK\),([a-z0-9-]+)\)", makefile))
    checks.update(re.findall(r'\$\$CHECK" != "([a-z0-9-]+)"', makefile))
    return checks


def extract_makefile_e2e_skip_embedding_scenarios() -> set[str]:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(r'if \[\[ "\$\$SCENARIO" =~ \^\(([^)]*)\)\$\$ \]\]', makefile)
    if not match:
        return set()
    return {scenario for scenario in match.group(1).split("|") if scenario}


def extract_playwright_targets() -> tuple[set[str], set[str]]:
    text = V020_E2E_SPEC.read_text(encoding="utf-8")
    titles = re.findall(r'test\("([^"]+)"', text)
    e2e: set[str] = set()
    visual: set[str] = set()
    for title in titles:
        e2e.update(re.findall(r"\b(v020-[a-z0-9-]+)\b", title))
        if title.startswith("visual-"):
            visual_target = title.split("：", 1)[0].split(":", 1)[0]
            visual.add(visual_target)
            visual.add(visual_target.removeprefix("visual-"))
    return e2e, visual


def extract_verify_visual_gate_checks() -> set[str]:
    text = VERIFY_VISUAL_GATE.read_text(encoding="utf-8")
    return set(re.findall(r'check == "([a-z0-9-]+)"', text))


def extract_current_readme_implemented_targets(readme: str) -> dict[str, set[str]]:
    paragraphs = [paragraph.strip() for paragraph in readme.split("\n\n")]
    target_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if paragraph.startswith("当前仓库已实现") or paragraph.startswith("近期新增已实现")
    ]
    targets = {"db": set(), "api": set(), "e2e": set(), "visual": set()}
    for paragraph in target_paragraphs:
        targets["db"].update(re.findall(r"make verify-db CHECK=([a-z0-9-]+)", paragraph))
        targets["api"].update(re.findall(r"make verify-api-contract CHECK=([a-z0-9-]+)", paragraph))
        targets["e2e"].update(re.findall(r"make verify-e2e SCENARIO=([a-z0-9-]+)", paragraph))
        targets["visual"].update(re.findall(r"make verify-visual CHECK=([a-z0-9-]+)", paragraph))
    return targets


def check_v020_target_inventory(readme: str) -> list[str]:
    errors: list[str] = []
    documented = extract_current_readme_implemented_targets(readme)
    supported_db = extract_python_mapping_keys(VERIFY_DB)
    supported_api = extract_python_mapping_keys(VERIFY_API_CONTRACT)
    supported_e2e, playwright_visual = extract_playwright_targets()
    supported_visual = extract_makefile_visual_checks()
    supported_visual.update(extract_verify_visual_gate_checks())

    checks = [
        ("make verify-db", "CHECK", documented["db"], supported_db),
        ("make verify-api-contract", "CHECK", documented["api"], supported_api),
        ("make verify-e2e", "SCENARIO", documented["e2e"], supported_e2e),
        ("make verify-visual", "CHECK", documented["visual"], supported_visual),
    ]
    for command, variable, declared, supported in checks:
        missing = sorted(declared - supported)
        for target in missing:
            errors.append(f"{V020_SPEC_DIR / 'README.md'}: 已实现清单声明 `{command} {variable}={target}`，但当前源码未支持该 target")
        undocumented = sorted(supported - declared)
        for target in undocumented:
            errors.append(f"{V020_SPEC_DIR / 'README.md'}: 当前源码支持 `{command} {variable}={target}`，但已实现清单未声明该 target")

    visual_without_tests = sorted(
        documented["visual"]
        - playwright_visual
        - extract_verify_visual_gate_checks()
        - {"design-tokens", "visual-system"}
    )
    for target in visual_without_tests:
        errors.append(f"{V020_SPEC_DIR / 'README.md'}: 已实现清单声明 `make verify-visual CHECK={target}`，但缺少对应 `visual-{target}` Playwright 场景")

    e2e_skip_embedding = extract_makefile_e2e_skip_embedding_scenarios()
    forbidden_skip = sorted(DASHSCOPE_REQUIRED_E2E_SCENARIOS & e2e_skip_embedding)
    for scenario in forbidden_skip:
        errors.append(f"{MAKEFILE}: `SCENARIO={scenario}` 需要真实 DashScope 成功路径，不得进入 --skip-embedding 白名单")
    return errors


def check_v020_dashscope_blocker_checklist(readme: str) -> list[str]:
    errors: list[str] = []
    heading = "## 集中阻塞确认清单"
    if heading not in readme:
        return [f"{V020_SPEC_DIR / 'README.md'}: 缺少集中阻塞确认清单"]
    section = readme.split(heading, 1)[1].split("\n## ", 1)[0]
    required_commands = [
        *(f"make verify-e2e SCENARIO={scenario}" for scenario in sorted(DASHSCOPE_REQUIRED_E2E_SCENARIOS)),
        "make evidence-package-with-tests",
    ]
    for command in required_commands:
        if command not in section:
            errors.append(f"{V020_SPEC_DIR / 'README.md'}: 集中阻塞确认清单缺少 `{command}`")
    required_constraints = [
        "不得降级为 mock",
        "固定向量成功路径",
        "`--skip-embedding`",
        "有效 DashScope",
        "`DASHSCOPE_API_KEY`",
        "运行环境中设置",
        "必须保持阻塞",
        "不得包含真实 API key、token、secret 或 password",
    ]
    for constraint in required_constraints:
        if constraint not in section:
            errors.append(f"{V020_SPEC_DIR / 'README.md'}: 集中阻塞确认清单缺少约束 `{constraint}`")
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
    errors.extend(check_v020_target_inventory(readme))
    errors.extend(check_v020_dashscope_blocker_checklist(readme))

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
    print("v0.2.0 draft spec structure, target inventory, DashScope skip allowlist, and blocker checklist checks passed")


if __name__ == "__main__":
    main()
