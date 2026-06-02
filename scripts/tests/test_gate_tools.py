from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import verify_release_gate  # noqa: E402
from scripts.collect_evidence import redact, render_command, visual_evidence_summary  # noqa: E402
from scripts.scan_secrets import scan_text  # noqa: E402
from scripts.verify_release_gate import check_v020_target_inventory  # noqa: E402


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
    assert "target inventory, and DashScope skip allowlist checks passed" in result.stdout


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


def test_processing_no_text_layer_reason_uses_v020_contract() -> None:
    processing_source = (ROOT / "backend/app/processing.py").read_text(encoding="utf-8")
    assert "v0.1.0 不进入 OCR" not in processing_source
    assert "PDF 无可提取文字层，v0.2.0 不进入 OCR" in processing_source
