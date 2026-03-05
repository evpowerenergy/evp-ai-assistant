"""
Format RAG results as natural language for LLM context
"""


def format_rag_response(rag_results: list, citations: list, user_message: str) -> str:
    """Format RAG results as natural language response"""
    if not rag_results:
        return "ไม่พบเอกสารที่เกี่ยวข้อง"

    # Combine content from all results (no limit)
    content_parts = []
    for result in rag_results:
        content = result.get("content", "")
        if content:
            content_parts.append(content)

    response = "\n\n".join(content_parts)

    # Add citations
    if citations:
        response += f"\n\nอ้างอิง: {', '.join(citations)}"

    return response
