"""Tests for structure-aware chunking."""
from app.services.chunking import build_chunks
from app.services.document_extractor import ExtractedDocument


def test_markdown_section_chunking():
    text = "# Intro\nHello world.\n\n## Steps\nStep one here.\nStep two here."
    extracted = ExtractedDocument(text=text)
    specs = build_chunks(extracted, title="Test", source_filename="doc.md")
    parents = [s for s in specs if s.chunk_level == "parent"]
    children = [s for s in specs if s.chunk_level == "child"]
    assert len(parents) >= 1
    assert len(children) >= 1
    assert all(s.parent_index is not None for s in children)


def test_short_text_single_chunk():
    extracted = ExtractedDocument(text="Short document text for testing.")
    specs = build_chunks(extracted, title="Short", source_filename="short.txt")
    children = [s for s in specs if s.chunk_level == "child"]
    assert len(children) >= 1


def test_page_based_chunking():
    from app.services.document_extractor import PageText

    extracted = ExtractedDocument(
        text="Page one.\n\nPage two.",
        pages=[
            PageText(page_number=1, text="Page one."),
            PageText(page_number=2, text="Page two."),
        ],
    )
    specs = build_chunks(extracted, title="PDF", source_filename="doc.pdf")
    child_meta = [s.metadata for s in specs if s.chunk_level == "child"]
    assert any(m.get("page_number") == 1 for m in child_meta)
