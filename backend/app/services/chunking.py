"""
Structure-aware chunking with optional parent-child pairs for contextual retrieval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings
from app.services.document_extractor import ExtractedDocument, PageText

CHUNK_END_MARKERS = [". ", ".\n", "! ", "!\n", "? ", "?\n", "\n\n"]


@dataclass
class ChunkSpec:
    content: str
    chunk_index: int
    chunk_level: str = "child"
    parent_index: Optional[int] = None
    metadata: dict = field(default_factory=dict)


def _split_by_size(text: str, chunk_size: int, overlap: int) -> List[str]:
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for marker in CHUNK_END_MARKERS:
                pos = text.rfind(marker, start, end)
                if pos != -1:
                    end = pos + len(marker)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = max(end - overlap, start + 1)
        if start >= len(text):
            break
    return chunks


def _markdown_sections(text: str) -> List[tuple[str, str]]:
    """Return (section_title, section_body) pairs."""
    lines = text.splitlines()
    sections: List[tuple[str, str]] = []
    current_title = ""
    current_lines: List[str] = []

    for line in lines:
        if re.match(r"^#{1,3}\s+", line):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = re.sub(r"^#+\s*", "", line).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines or current_title:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if not sections:
        return [("", text)]
    return [(t, b) for t, b in sections if b]


def _page_sections(pages: List[PageText]) -> List[tuple[str, str]]:
    return [(f"หน้า {p.page_number}", p.text) for p in pages if p.text.strip()]


def build_chunks(
    extracted: ExtractedDocument,
    *,
    title: str,
    source_filename: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[ChunkSpec]:
    chunk_size = chunk_size or settings.KB_CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.KB_CHUNK_OVERLAP

    specs: List[ChunkSpec] = []
    parent_index = 0
    child_index = 0

    # Choose section split strategy
    if extracted.pages:
        sections = _page_sections(extracted.pages)
    elif source_filename.lower().endswith(".md"):
        sections = _markdown_sections(extracted.text)
    else:
        sections = [("", extracted.text)]

    for section_title, section_body in sections:
        if not section_body.strip():
            continue

        parent_meta = {
            "title": title,
            "source_filename": source_filename,
            "section_title": section_title or None,
            "chunk_level": "parent",
        }
        specs.append(
            ChunkSpec(
                content=section_body,
                chunk_index=parent_index,
                chunk_level="parent",
                metadata=parent_meta,
            )
        )
        current_parent = parent_index
        parent_index += 1

        for piece in _split_by_size(section_body, chunk_size, chunk_overlap):
            child_meta = {
                "title": title,
                "source_filename": source_filename,
                "section_title": section_title or None,
                "chunk_level": "child",
                "parent_chunk_index": current_parent,
            }
            if extracted.pages and section_title.startswith("หน้า "):
                try:
                    child_meta["page_number"] = int(section_title.replace("หน้า ", "").strip())
                except ValueError:
                    pass

            specs.append(
                ChunkSpec(
                    content=piece,
                    chunk_index=child_index,
                    chunk_level="child",
                    parent_index=current_parent,
                    metadata=child_meta,
                )
            )
            child_index += 1

    child_count = sum(1 for s in specs if s.chunk_level == "child")
    if child_count > settings.KB_MAX_CHUNKS:
        raise ValueError(
            f"Document produces {child_count} chunks (max {settings.KB_MAX_CHUNKS}). "
            "Split into smaller files."
        )

    for spec in specs:
        if spec.chunk_level == "child":
            spec.metadata["total_child_chunks"] = child_count

    return specs
