"""
Knowledge-base document CRUD (service role).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services import kb_storage
from app.services.vector_store import delete_chunks_for_document
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def list_documents(
    *,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    supabase = get_supabase_client()
    query = (
        supabase.table("kb_documents")
        .select(
            "id, title, file_path, file_type, file_size, status, chunk_count, "
            "category, created_at, updated_at, indexed_at, error_message, uploaded_by"
        )
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)
    result = query.execute()
    return result.data or []


async def get_document(document_id: str) -> Optional[Dict[str, Any]]:
    supabase = get_supabase_client()
    result = (
        supabase.table("kb_documents")
        .select("*")
        .eq("id", document_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


async def get_document_status(document_id: str) -> Dict[str, Any]:
    doc = await get_document(document_id)
    if not doc:
        return {"found": False}

    supabase = get_supabase_client()
    jobs = (
        supabase.table("kb_ingest_jobs")
        .select("*")
        .eq("document_id", document_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    job = (jobs.data or [None])[0]
    return {
        "found": True,
        "document": doc,
        "job": job,
    }


async def delete_document(document_id: str) -> bool:
    doc = await get_document(document_id)
    if not doc:
        return False

    await delete_chunks_for_document(document_id)
    kb_storage.delete_original(doc.get("storage_path"), doc.get("storage_bucket"))

    supabase = get_supabase_client()
    supabase.table("kb_ingest_jobs").delete().eq("document_id", document_id).execute()
    supabase.table("kb_documents").delete().eq("id", document_id).execute()
    logger.info("Deleted KB document %s", document_id)
    return True


async def get_download_url(document_id: str, expires_sec: int = 3600) -> str:
    doc = await get_document(document_id)
    if not doc or not doc.get("storage_path"):
        raise ValueError("Document or storage file not found")
    return kb_storage.create_signed_download_url(
        doc["storage_path"],
        bucket=doc.get("storage_bucket"),
        expires_sec=expires_sec,
    )
