"""
Format AI responses for LINE (plain text, no markdown tables).
"""
import re
from typing import List, Optional


def _strip_markdown(text: str) -> str:
    """Light markdown cleanup for LINE plain text."""
    t = text
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*[-*]\s+", "• ", t, flags=re.MULTILINE)
    return t


def format_for_line(response: str, citations: Optional[List[str]] = None) -> str:
    """Convert AI response + citations to LINE-friendly text."""
    text = _strip_markdown(response or "").strip()
    if citations:
        unique = []
        for c in citations:
            if c and c not in unique:
                unique.append(c)
        if unique:
            text += "\n\n---\nอ้างอิง:\n" + "\n".join(f"• {u}" for u in unique[:5])
    return text
