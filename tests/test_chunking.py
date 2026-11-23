import pytest

from app.services.chunking import chunk_pages


def test_short_page_is_one_chunk():
    chunks = chunk_pages(["Hello   world.\n\nSecond line."], size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0].content == "Hello world. Second line."
    assert chunks[0].page == 1


def test_chunks_respect_size_and_overlap():
    text = " ".join(f"Sentence number {i}." for i in range(200))
    chunks = chunk_pages([text], size=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c.content) <= 200 for c in chunks)
    # Consecutive chunks share text, so no sentence is lost at a boundary
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        assert prev.content[-20:].split()[-1] in nxt.content


def test_prefers_sentence_boundaries():
    text = "A" * 120 + ". " + "B" * 120
    chunks = chunk_pages([text], size=200, overlap=0)
    assert chunks[0].content.endswith(".")


def test_chunks_never_span_pages_and_empty_pages_are_skipped():
    chunks = chunk_pages(["first page", "", "third page"], size=100, overlap=10)
    assert [(c.page, c.content) for c in chunks] == [(1, "first page"), (3, "third page")]


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_pages(["x"], size=10, overlap=10)
