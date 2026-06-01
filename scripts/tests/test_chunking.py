from app.processing import normalize_page_text, split_page_text, split_page_text_with_offsets


def test_split_page_text_keeps_short_page_as_one_chunk() -> None:
    assert split_page_text("第一段\n第二段") == ["第一段\n第二段"]


def test_split_page_text_limits_long_chunks() -> None:
    text = ("甲" * 1200) + "\n\n" + ("乙" * 1200)
    chunks = split_page_text(text)
    assert len(chunks) == 2
    assert all(len(chunk) <= 2000 for chunk in chunks)


def test_split_page_text_splits_single_long_paragraph() -> None:
    chunks = split_page_text("甲" * 4500)
    assert [len(chunk) for chunk in chunks] == [2000, 2000, 500]


def test_split_page_text_ignores_blank_text() -> None:
    assert split_page_text(" \n\t ") == []


def test_split_page_text_with_offsets_tracks_repeated_chunks() -> None:
    text = ("重复" * 600) + "\n\n" + ("重复" * 600)
    chunks = split_page_text_with_offsets(text)

    assert len(chunks) == 2
    assert chunks[0][1:] == (0, 1200)
    assert chunks[1][1:] == (1202, 2402)


def test_split_page_text_offsets_match_normalized_text() -> None:
    normalized = normalize_page_text("  第一段  \n \n  第二段  ")
    chunks = split_page_text_with_offsets("  第一段  \n \n  第二段  ")

    assert normalized == "第一段 \n \n 第二段"
    assert chunks == [(normalized, 0, len(normalized))]


def test_split_page_text_offsets_preserve_spaced_blank_line_separators() -> None:
    text = ("甲" * 700) + "  \n \n  " + ("乙" * 700) + "  \n \n  " + ("丙" * 700)
    normalized = normalize_page_text(text)
    chunks = split_page_text_with_offsets(text)

    assert len(chunks) == 2
    for chunk, start, end in chunks:
        assert normalized[start:end] == chunk
