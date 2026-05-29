from __future__ import annotations

from pathlib import Path

import fitz
import pytest


FIXTURE_DIR = Path("tests/fixtures")


def _pdf_text_stats(path: Path) -> tuple[int, int]:
    with fitz.open(path) as pdf:
        text_chars = sum(len(page.get_text("text").strip()) for page in pdf)
        return pdf.page_count, text_chars


def test_v010_required_fixtures_exist() -> None:
    required = {
        "text-layer-material.pdf",
        "question-source.pdf",
        "question.txt",
        "not-pdf.txt",
        "broken.pdf",
        "scanned.pdf",
        "unmatched-question.txt",
    }

    missing = [name for name in sorted(required) if not (FIXTURE_DIR / name).exists()]

    assert missing == []


def test_text_layer_material_has_extractable_text() -> None:
    page_count, text_chars = _pdf_text_stats(FIXTURE_DIR / "text-layer-material.pdf")

    assert page_count > 0
    assert text_chars > 0


def test_question_source_has_extractable_text_and_question_fixture() -> None:
    page_count, text_chars = _pdf_text_stats(FIXTURE_DIR / "question-source.pdf")
    question_text = (FIXTURE_DIR / "question.txt").read_text(encoding="utf-8").strip()

    assert page_count > 0
    assert text_chars > 0
    assert question_text


def test_scanned_fixture_has_no_text_layer() -> None:
    page_count, text_chars = _pdf_text_stats(FIXTURE_DIR / "scanned.pdf")

    assert page_count > 0
    assert text_chars == 0


def test_broken_pdf_fixture_is_not_openable() -> None:
    with pytest.raises(fitz.FileDataError):
        fitz.open(FIXTURE_DIR / "broken.pdf")
