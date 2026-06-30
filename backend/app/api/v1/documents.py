"""
Knowledge-base document management API.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import Optional

from app.core.auth import require_ai_assistant_access, require_role
from app.core.audit import log_audit
from app.services import document_service
from app.services.ingest_service import run_ingest_pipeline
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

require_super_admin = require_role(["super_admin"])


@router.get("/documents")
async def list_documents(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: dict = Depends(require_ai_assistant_access),
):
    docs = await document_service.list_documents(
        limit=limit, offset=offset, status=status, category=category
    )
    return {"documents": docs, "count": len(docs)}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(require_ai_assistant_access),
):
    doc = await document_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{document_id}/status")
async def get_document_status(
    document_id: str,
    current_user: dict = Depends(require_ai_assistant_access),
):
    status_payload = await document_service.get_document_status(document_id)
    if not status_payload.get("found"):
        raise HTTPException(status_code=404, detail="Document not found")
    return status_payload


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: dict = Depends(require_super_admin),
):
    try:
        url = await document_service.get_download_url(document_id)
        return {"download_url": url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(require_super_admin),
):
    deleted = await document_service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    await log_audit(
        user_id=current_user.get("id"),
        action="document_delete",
        resource="kb_documents",
        request_data={"document_id": document_id},
    )
    return {"status": "deleted", "document_id": document_id}


@router.post("/documents/{document_id}/reindex")
async def reindex_document_endpoint(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_super_admin),
):
    try:
        from app.services.ingest_service import reindex_document_prepare

        job_id, pipeline_kwargs = await reindex_document_prepare(
            document_id, current_user.get("id")
        )
        background_tasks.add_task(run_ingest_pipeline, **pipeline_kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "status": "accepted",
        "document_id": document_id,
        "job_id": job_id,
    }
