"""
Vector Store Service (pgvector) — production hybrid retrieval.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import settings
from app.services.chunking import ChunkSpec
from app.services.embedding import get_embeddings
from app.services.query_rewrite import rewrite_query_for_search
from app.services.reranker import rerank_chunks
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

_parent_id_by_index: Dict[str, Dict[int, str]] = {}


def get_document_source(document_id: str) -> str:
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("kb_documents")
            .select("title, file_path")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )
        row = (result.data or [{}])[0]
        return row.get("title") or row.get("file_path") or "Unknown"
    except Exception:
        return "Unknown"


async def delete_chunks_for_document(document_id: str) -> None:
    supabase = get_supabase_client()
    supabase.table("kb_chunks").delete().eq("document_id", document_id).execute()
    _parent_id_by_index.pop(document_id, None)


async def index_chunk_specs(document_id: str, specs: List[ChunkSpec]) -> int:
    """Embed and store parent + child chunks. Returns child chunk count."""
    supabase = get_supabase_client()
    embeddings = get_embeddings()
    parent_map: Dict[int, str] = {}
    child_specs = [s for s in specs if s.chunk_level == "child"]
    parent_specs = [s for s in specs if s.chunk_level == "parent"]

    # Insert parents first (no embedding)
    for spec in parent_specs:
        chunk_id = str(uuid4())
        parent_map[spec.chunk_index] = chunk_id
        supabase.table("kb_chunks").insert(
            {
                "id": chunk_id,
                "document_id": document_id,
                "content": spec.content,
                "chunk_index": spec.chunk_index,
                "chunk_level": "parent",
                "metadata": spec.metadata,
            }
        ).execute()

    _parent_id_by_index[document_id] = parent_map

    if not child_specs:
        return 0

    texts = [s.content for s in child_specs]
    batch_size = 20
    all_vectors: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_vectors.extend(embeddings.embed_documents(batch))

    rows = []
    for spec, vector in zip(child_specs, all_vectors):
        parent_uuid = None
        if spec.parent_index is not None:
            parent_uuid = parent_map.get(spec.parent_index)
        rows.append(
            {
                "id": str(uuid4()),
                "document_id": document_id,
                "content": spec.content,
                "embedding": vector,
                "chunk_index": spec.chunk_index,
                "chunk_level": "child",
                "parent_chunk_id": parent_uuid,
                "metadata": spec.metadata,
            }
        )

    for i in range(0, len(rows), batch_size):
        supabase.table("kb_chunks").insert(rows[i : i + batch_size]).execute()

    return len(child_specs)


def _load_parent_context(document_id: str, parent_chunk_id: Optional[str]) -> str:
    if not parent_chunk_id:
        return ""
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("kb_chunks")
            .select("content")
            .eq("id", parent_chunk_id)
            .limit(1)
            .execute()
        )
        row = (result.data or [{}])[0]
        return row.get("content") or ""
    except Exception:
        return ""


async def search_similar(
    query: str,
    limit: int = 5,
    threshold: float | None = None,
    category_filter: Optional[str] = None,
    *,
    rewrite_query: bool = True,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Hybrid search + optional rerank. Returns (results, retrieval_meta).
    """
    start = time.time()
    threshold = threshold if threshold is not None else settings.KB_SIMILARITY_THRESHOLD
    search_text = await rewrite_query_for_search(query) if rewrite_query else query

    embeddings = get_embeddings()
    query_embedding = embeddings.embed_query(search_text)
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    supabase = get_supabase_client()
    candidates: List[Dict[str, Any]] = []

    try:
        if settings.KB_ENABLE_HYBRID_SEARCH:
            result = supabase.rpc(
                "hybrid_search_kb",
                {
                    "query_embedding": embedding_str,
                    "query_text": search_text,
                    "match_count": settings.KB_RETRIEVE_CANDIDATES,
                    "similarity_threshold": threshold,
                    "category_filter": category_filter,
                },
            ).execute()
            rows = result.data or []
        else:
            result = supabase.rpc(
                "match_kb_chunks",
                {
                    "query_embedding": embedding_str,
                    "match_threshold": threshold,
                    "match_count": settings.KB_RETRIEVE_CANDIDATES,
                },
            ).execute()
            rows = result.data or []

        for row in rows:
            doc_id = row.get("document_id")
            parent_id = row.get("parent_chunk_id")
            parent_ctx = _load_parent_context(doc_id, parent_id) if parent_id else ""
            content = row.get("content") or ""
            if parent_ctx and parent_ctx not in content:
                content = f"[บริบทส่วน]\n{parent_ctx[:1500]}\n\n[ส่วนที่เกี่ยวข้อง]\n{content}"

            sim = row.get("fused_score") or row.get("vector_score")
            if sim is None and row.get("distance") is not None:
                sim = 1 - float(row.get("distance", 1))

            candidates.append(
                {
                    "id": row.get("id"),
                    "content": content,
                    "document_id": doc_id,
                    "chunk_index": row.get("chunk_index", 0),
                    "similarity": float(sim or 0),
                    "metadata": row.get("metadata") or {},
                    "source": get_document_source(doc_id) if doc_id else "Unknown",
                }
            )
    except Exception as e:
        logger.error("Vector/hybrid search error: %s", e)
        if settings.KB_ENABLE_HYBRID_SEARCH:
            # Fallback to legacy RPC
            try:
                result = supabase.rpc(
                    "match_kb_chunks",
                    {
                        "query_embedding": embedding_str,
                        "match_threshold": max(threshold - 0.1, 0.4),
                        "match_count": settings.KB_RETRIEVE_CANDIDATES,
                    },
                ).execute()
                for row in result.data or []:
                    doc_id = row.get("document_id")
                    candidates.append(
                        {
                            "id": row.get("id"),
                            "content": row.get("content", ""),
                            "document_id": doc_id,
                            "chunk_index": row.get("chunk_index", 0),
                            "similarity": 1 - float(row.get("distance", 1)),
                            "metadata": row.get("metadata") or {},
                            "source": get_document_source(doc_id) if doc_id else "Unknown",
                        }
                    )
            except Exception as e2:
                logger.error("Fallback vector search error: %s", e2)

    if not candidates and threshold > 0.30:
        return await search_similar(
            query,
            limit=limit,
            threshold=max(threshold - 0.08, 0.30),
            category_filter=category_filter,
            rewrite_query=False,
        )

    ranked = await rerank_chunks(query, candidates, top_k=limit)
    elapsed_ms = int((time.time() - start) * 1000)
    meta = {
        "query_rewrite": search_text,
        "candidates": len(candidates),
        "returned": len(ranked),
        "top_similarities": [c.get("similarity") for c in ranked[:5]],
        "rerank_scores": [c.get("rerank_score") for c in ranked[:5]],
        "retrieval_ms": elapsed_ms,
        "selected_chunks": [
            {
                "document_id": c.get("document_id"),
                "chunk_index": c.get("chunk_index"),
                "source": c.get("source"),
            }
            for c in ranked
        ],
    }
    logger.info(
        "KB search: query=%s... candidates=%s returned=%s ms=%s",
        query[:40],
        len(candidates),
        len(ranked),
        elapsed_ms,
    )
    return ranked, meta


# Legacy sync helper for backward compatibility
async def ingest_document(
    title: str,
    content: str,
    file_path: Optional[str] = None,
    file_type: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> str:
    """Legacy text-only ingest (tests / simple path)."""
    from app.services.document_extractor import ExtractedDocument
    from app.services.chunking import build_chunks

    document_id = str(uuid4())
    supabase = get_supabase_client()
    supabase.table("kb_documents").insert(
        {
            "id": document_id,
            "title": title,
            "file_path": file_path,
            "file_type": file_type,
            "uploaded_by": uploaded_by,
            "status": "processing",
        }
    ).execute()

    extracted = ExtractedDocument(text=content)
    specs = build_chunks(extracted, title=title, source_filename=file_path or "text")
    count = await index_chunk_specs(document_id, specs)
    supabase.table("kb_documents").update(
        {"status": "ready", "chunk_count": count}
    ).eq("id", document_id).execute()
    return document_id
