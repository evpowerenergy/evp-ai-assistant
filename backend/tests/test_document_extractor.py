"""Tests for document text extraction."""
import pytest

from app.services.document_extractor import DocumentExtractionError, extract_document
from app.services.ingest_service import content_hash


def test_extract_plain_text():
    raw = "นี่คือเอกสารทดสอบสำหรับระบบ knowledge base".encode("utf-8")
    doc = extract_document(raw, "test.txt", "text/plain")
    assert "ทดสอบ" in doc.text
    assert doc.metadata.get("extractor") == "text"


def test_extract_markdown():
    raw = "# Title\n\nBody content here.".encode("utf-8")
    doc = extract_document(raw, "readme.md", "text/markdown")
    assert "Body content" in doc.text


def test_reject_unsupported_extension():
    with pytest.raises(DocumentExtractionError):
        extract_document(b"data", "file.exe", "application/octet-stream")


def test_reject_legacy_doc():
    with pytest.raises(DocumentExtractionError) as exc:
        extract_document(b"fake", "legacy.doc", "application/msword")
    assert "docx" in str(exc.value).lower()


def test_content_hash_stable():
    text = "same content"
    h1 = content_hash(text)
    h2 = content_hash(text)
    assert h1 == h2
    assert len(h1) == 64
