from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from scripts import reset_demo, verify_release_gate  # noqa: E402
from scripts.collect_evidence import (  # noqa: E402
    TEST_COMMAND,
    V020_COMMANDS,
    redact,
    render_command,
    visual_evidence_summary,
)
from scripts.scan_secrets import scan_text  # noqa: E402
from scripts.verify_release_gate import (  # noqa: E402
    check_v020_dashscope_blocker_checklist,
    check_v020_target_inventory,
    extract_python_mapping_keys,
)


def run_script(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", f"scripts/{name}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_release_gate_script_passes() -> None:
    result = run_script("verify_release_gate.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "release gate spec checks passed" in result.stdout
    assert "target inventory, DashScope skip allowlist, and blocker checklist checks passed" in result.stdout


def test_secret_scan_passes() -> None:
    result = run_script("scan_secrets.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "secret scan passed" in result.stdout


def test_secret_scan_allows_config_variables() -> None:
    findings = scan_text("client = OpenAI(api_key=settings.dashscope_api_key)\n", "sample.py")
    assert findings == []


def test_secret_scan_blocks_hardcoded_fallback_without_leaking_value() -> None:
    secret = "sk-" + "a" * 32
    findings = scan_text(f'api_key = os.getenv("DASHSCOPE_API_KEY", "{secret}")\n', "sample.py")
    assert findings
    assert all(secret not in finding for finding in findings)


def test_secret_scan_blocks_hardcoded_settings_assignment() -> None:
    secret = "sk-" + "b" * 32
    findings = scan_text(f'settings.api_key = "{secret}"\n', "sample.py")
    assert findings
    assert all(secret not in finding for finding in findings)


def test_collect_evidence_redacts_secrets() -> None:
    secret = "sk-" + "c" * 32
    redacted = redact(f"api_key={secret}\nDASHSCOPE_API_KEY={secret}\nAuthorization: Bearer {secret}\nCookie: session={secret}")
    assert secret not in redacted
    assert "<redacted>" in redacted
    assert "Authorization: <redacted>" in redacted
    assert "Cookie: <redacted>" in redacted


def test_collect_evidence_renders_v020_fields() -> None:
    rendered = render_command(
        ["make", "verify-visual", "CHECK=screenshot-matrix"],
        0,
        "ok",
        1.25,
        "fixed visual seed matrix",
        "tmp/v0.2.0-visual-evidence/",
    )
    assert "- 结论：通过" in rendered
    assert "- 执行时间：`1.25s`" in rendered
    assert "- 数据准备命令：fixed visual seed matrix" in rendered
    assert "- 证据路径：tmp/v0.2.0-visual-evidence/" in rendered


def test_collect_evidence_visual_summary_is_redaction_safe() -> None:
    summary = "\n".join(visual_evidence_summary())
    assert "tmp/v0.2.0-visual-evidence" in summary
    assert "sk-" not in summary


def test_collect_evidence_renders_visual_summary_after_screenshot_matrix_command() -> None:
    collect_evidence_source = (ROOT / "scripts/collect_evidence.py").read_text(encoding="utf-8")
    command_order = [item["command"] for item in V020_COMMANDS]
    screenshot_index = command_order.index(["make", "verify-visual", "CHECK=screenshot-matrix"])
    assert command_order.index(TEST_COMMAND) > screenshot_index
    assert collect_evidence_source.index("command_sections.append(") < collect_evidence_source.index("sections.extend(visual_evidence_summary())")


def test_v020_target_inventory_matches_current_sources() -> None:
    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    assert check_v020_target_inventory(readme) == []


def test_v020_target_inventory_rejects_documented_missing_target() -> None:
    readme = "当前仓库已实现 `make verify-e2e SCENARIO=v020-not-real`。"
    errors = check_v020_target_inventory(readme)
    assert errors
    assert any("v020-not-real" in error for error in errors)


def test_v020_target_inventory_rejects_undocumented_supported_target() -> None:
    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    readme = readme.replace("`make verify-db CHECK=v020-schema`、", "", 1)
    errors = check_v020_target_inventory(readme)
    assert errors
    assert any("当前源码支持 `make verify-db CHECK=v020-schema`" in error for error in errors)


def test_v020_target_inventory_rejects_dashscope_scenario_in_skip_embedding(monkeypatch, tmp_path: Path) -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    makefile = makefile.replace(
        "v020-focus-mode-restore)$$",
        "v020-focus-mode-restore|v020-full-regression)$$",
        1,
    )
    patched_makefile = tmp_path / "Makefile"
    patched_makefile.write_text(makefile, encoding="utf-8")
    monkeypatch.setattr(verify_release_gate, "MAKEFILE", patched_makefile)

    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    errors = check_v020_target_inventory(readme)
    assert any("SCENARIO=v020-full-regression" in error and "--skip-embedding" in error for error in errors)


def test_python_mapping_key_extraction_ignores_fixture_dicts(tmp_path: Path) -> None:
    script = tmp_path / "verify_like.py"
    script.write_text(
        """
FIXTURES = {"v020-not-a-target": "fixture"}


def helper() -> None:
    checks = {"v020-helper-only": object()}


def main() -> None:
    checks = {
        "v020-real-target": object(),
        "legacy-target": object(),
    }
    checks["v020-real-target"]()
""",
        encoding="utf-8",
    )
    assert extract_python_mapping_keys(script) == {"v020-real-target"}


def test_reset_demo_clears_processing_queue(monkeypatch) -> None:
    removed_jobs: list[tuple[str, bool]] = []

    class FakeQueue:
        def __init__(self, name: str, connection: object) -> None:
            self.name = name
            self.connection = connection
            self.emptied = False

        def empty(self) -> None:
            self.emptied = True

    fake_queues: list[FakeQueue] = []

    def fake_queue(name: str, connection: object) -> FakeQueue:
        queue = FakeQueue(name, connection)
        fake_queues.append(queue)
        return queue

    class FakeRegistry:
        def __init__(self, queue: FakeQueue) -> None:
            self.queue = queue

        def get_job_ids(self) -> list[str]:
            return [f"{self.__class__.__name__}-old"]

        def remove(self, job_id: str, delete_job: bool = False) -> None:
            removed_jobs.append((job_id, delete_job))

    monkeypatch.setattr(reset_demo.Redis, "from_url", lambda url: object())
    monkeypatch.setattr(reset_demo, "Queue", fake_queue)
    for name in (
        "StartedJobRegistry",
        "DeferredJobRegistry",
        "FailedJobRegistry",
        "FinishedJobRegistry",
        "ScheduledJobRegistry",
        "CanceledJobRegistry",
    ):
        monkeypatch.setattr(reset_demo, name, FakeRegistry)

    reset_demo.clear_processing_queue()

    assert fake_queues[0].name == "suton"
    assert fake_queues[0].emptied
    assert len(removed_jobs) == 6
    assert all(delete_job for _, delete_job in removed_jobs)


def test_v020_dashscope_blocker_checklist_matches_current_readme() -> None:
    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    assert check_v020_dashscope_blocker_checklist(readme) == []


def test_v020_dashscope_blocker_checklist_rejects_missing_command() -> None:
    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    readme = readme.replace("- `make verify-e2e SCENARIO=v020-question-search`\n", "", 1)
    errors = check_v020_dashscope_blocker_checklist(readme)
    assert any("v020-question-search" in error for error in errors)


def test_v020_dashscope_blocker_checklist_rejects_missing_no_downgrade_constraint() -> None:
    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    readme = readme.replace("后续回归、证据包重跑和发布前审计不得降级为 mock、固定向量成功路径或 `--skip-embedding`。", "", 1)
    errors = check_v020_dashscope_blocker_checklist(readme)
    assert any("不得降级为 mock" in error for error in errors)
    assert any("固定向量成功路径" in error for error in errors)


def test_v020_dashscope_blocker_checklist_rejects_missing_valid_key_requirement() -> None:
    readme = (ROOT / "docs/spec/v0.2.0/README.md").read_text(encoding="utf-8")
    readme = readme.replace(
        "后续回归或证据包重跑时必须继续在运行环境中设置有效 DashScope `DASHSCOPE_API_KEY`，",
        "",
        1,
    )
    readme = readme.replace("有效 `DASHSCOPE_API_KEY`", "有效凭据", 1)
    errors = check_v020_dashscope_blocker_checklist(readme)
    assert any("有效 DashScope" in error for error in errors)
    assert any("DASHSCOPE_API_KEY" in error for error in errors)
    assert any("运行环境中设置" in error for error in errors)


def test_processing_no_text_layer_reason_uses_v020_contract() -> None:
    processing_source = (ROOT / "backend/app/processing.py").read_text(encoding="utf-8")
    assert "v0.1.0 不进入 OCR" not in processing_source
    assert "PDF 无可提取文字层，v0.2.0 不进入 OCR" in processing_source


def test_dashscope_missing_key_messages_are_version_neutral() -> None:
    checked_files = [
        ROOT / "backend/app/embedding.py",
        ROOT / "scripts/dev_check.py",
        ROOT / "scripts/doctor.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)

    assert "v0.1.0 要求的 DashScope embedding" not in source
    assert "v0.1.0 embedding 链路" not in source
    assert "缺少 DASHSCOPE_API_KEY，无法生成 Suton 要求的 DashScope embedding" in source
    assert "缺少 DASHSCOPE_API_KEY，无法满足 Suton DashScope embedding 链路" in source


def test_runtime_diagnostics_cli_description_is_version_neutral() -> None:
    doctor_source = (ROOT / "scripts/doctor.py").read_text(encoding="utf-8")

    assert "Suton v0.1.0 local runtime diagnostics" not in doctor_source
    assert "Suton local runtime diagnostics" in doctor_source
