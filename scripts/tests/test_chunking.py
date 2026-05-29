from app.processing import split_page_text


def test_split_page_text_keeps_short_page_as_one_chunk() -> None:
    assert split_page_text("第一段\n第二段") == ["第一段\n第二段"]


def test_split_page_text_limits_long_chunks() -> None:
    text = ("甲" * 1200) + "\n\n" + ("乙" * 1200)
    chunks = split_page_text(text)
    assert len(chunks) == 2
    assert all(len(chunk) <= 2000 for chunk in chunks)
