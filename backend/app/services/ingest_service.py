"""
Knowledge-base ingest orchestration (async job pipeline).
"""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from app.config import settings
from app.core.audit import log_audit
from app.services.chunking import ChunkSpec, build_chunks
from app.services.document_extractor import DocumentExtractionError, extract_document
from app.services import kb_storage
from app.services.vector_store import index_chunk_specs, delete_chunks_for_document
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def find_duplicate_by_hash(text_hash: str) -> Optional[Dict[str, Any]]:
    supabase = get_supabase_client()
    result = (
        supabase.table("kb_documents")
        .select("id, title, status")
        .eq("content_hash", text_hash)
        .eq("status", "ready")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


async def create_ingest_job(
    *,
    title: str,
    filename: str,
    file_type: Optional[str],
    file_size: int,
    uploaded_by: str,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    document_id = str(uuid4())
    supabase = get_supabase_client()
    doc_row = {
        "id": document_id,
        "title": title,
        "file_path": filename,
        "file_type": file_type,
        "file_size": file_size,
        "uploaded_by": uploaded_by,
        "storage_bucket": settings.KB_STORAGE_BUCKET,
        "status": "queued",
        "category": category,
        "version": 1,
    }
    supabase.table("kb_documents").insert(doc_row).execute()

    job_id = str(uuid4())
    job_row = {
        "id": job_id,
        "document_id": document_id,
        "status": "queued",
        "progress_pct": 0,
        "created_by": uploaded_by,
    }
    supabase.table("kb_ingest_jobs").insert(job_row).execute()
    return {"document_id": document_id, "job_id": job_id}


async def _update_job(job_id: str, **fields: Any) -> None:
    supabase = get_supabase_client()
    supabase.table("kb_ingest_jobs").update(fields).eq("id", job_id).execute()


async def _update_document(document_id: str, **fields: Any) -> None:
    supabase = get_supabase_client()
    supabase.table("kb_documents").update(fields).eq("id", document_id).execute()


async def run_ingest_pipeline(
    *,
    document_id: str,
    job_id: str,
    content_bytes: bytes,
    filename: str,
    title: str,
    file_type: Optional[str],
    uploaded_by: str,
    category: Optional[str] = None,
    allow_duplicate: bool = False,
) -> None:
    """Background pipeline: storage → extract → chunk → embed → ready."""
    try:
        await _update_job(
            job_id,
            status="processing",
            progress_pct=5,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        await _update_document(document_id, status="processing")

        await delete_chunks_for_document(document_id)

        storage_path = kb_storage.upload_original(document_id, filename, content_bytes)
        await _update_document(
            document_id,
            storage_path=storage_path,
            storage_bucket=settings.KB_STORAGE_BUCKET,
        )
        await _update_job(job_id, progress_pct=20)

        extracted = extract_document(content_bytes, filename, file_type)
        text_hash = content_hash(extracted.text)

        if not allow_duplicate:
            dup = await find_duplicate_by_hash(text_hash)
            if dup and dup.get("id") != document_id:
                raise DocumentExtractionError(
                    f"Duplicate content (existing document: {dup.get('title')} id={dup.get('id')})"
                )

        await _update_job(job_id, progress_pct=35)

        specs = build_chunks(
            extracted,
            title=title,
            source_filename=filename,
        )
        await _update_job(job_id, progress_pct=50)

        chunk_count = await index_chunk_specs(document_id, specs)
        await _update_job(job_id, progress_pct=90)

        now = datetime.now(timezone.utc).isoformat()
        await _update_document(
            document_id,
            status="ready",
            content_hash=text_hash,
            chunk_count=chunk_count,
            indexed_at=now,
            error_message=None,
            category=category,
        )
        await _update_job(
            job_id,
            status="completed",
            progress_pct=100,
            completed_at=now,
        )

        await log_audit(
            user_id=uploaded_by,
            action="document_ingest",
            resource="kb_documents",
            request_data={
                "document_id": document_id,
                "filename": filename,
                "chunk_count": chunk_count,
                "used_ocr": extracted.used_ocr,
            },
        )
        logger.info("Ingest complete document_id=%s chunks=%s", document_id, chunk_count)

    except Exception as e:
        logger.error("Ingest failed document_id=%s: %s", document_id, e)
        await delete_chunks_for_document(document_id)
        err = str(e)
        await _update_document(
            document_id,
            status="failed",
            error_message=err[:2000],
        )
        await _update_job(
            job_id,
            status="failed",
            error_message=err[:2000],
            completed_at=datetime.now(timezone.utc).isoformat(),
        )


def schedule_ingest(**kwargs: Any) -> None:
    """Fire-and-forget background ingest on the current event loop."""
    asyncio.create_task(run_ingest_pipeline(**kwargs))


async def reindex_document_prepare(document_id: str, uploaded_by: str):
    """Prepare reindex job; caller runs run_ingest_pipeline in background."""
    supabase = get_supabase_client()
    doc_result = (
        supabase.table("kb_documents")
        .select("*")
        .eq("id", document_id)
        .limit(1)
        .execute()
    )
    row = (doc_result.data or [None])[0]
    if not row:
        raise ValueError("Document not found")
    storage_path = row.get("storage_path")
    if not storage_path:
        raise ValueError("No stored original file to reindex")

    content_bytes = kb_storage.download_original(
        storage_path, bucket=row.get("storage_bucket")
    )

    await delete_chunks_for_document(document_id)

    job_id = str(uuid4())
    supabase.table("kb_ingest_jobs").insert(
        {
            "id": job_id,
            "document_id": document_id,
            "status": "queued",
            "progress_pct": 0,
            "created_by": uploaded_by,
        }
    ).execute()

    await _update_document(
        document_id,
        status="queued",
        version=(row.get("version") or 1) + 1,
        error_message=None,
    )

    pipeline_kwargs = dict(
        document_id=document_id,
        job_id=job_id,
        content_bytes=content_bytes,
        filename=row.get("file_path") or "reindex",
        title=row.get("title") or "Reindex",
        file_type=row.get("file_type"),
        uploaded_by=uploaded_by,
        category=row.get("category"),
        allow_duplicate=True,
    )
    return job_id, pipeline_kwargs


async def reindex_document(document_id: str, uploaded_by: str) -> str:
    job_id, kwargs = await reindex_document_prepare(document_id, uploaded_by)
    schedule_ingest(**kwargs)
    return job_id
