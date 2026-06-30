"""
Document Ingestion API (super_admin only, async job).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from typing import Optional

from app.core.auth import require_ai_assistant_access, require_role
from app.services.document_extractor import DocumentExtractionError
from app.services.ingest_service import (
    create_ingest_job,
    find_duplicate_by_hash,
    run_ingest_pipeline,
    content_hash,
)
from app.services.document_extractor import extract_document
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

require_super_admin = require_role(["super_admin"])


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_document_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    allow_duplicate: bool = Form(False),
    current_user: dict = Depends(require_super_admin),
):
    """
    Queue document ingestion into knowledge base.
    Supports: .txt, .md, .pdf, .docx
    """
    user_id = current_user.get("id")
    filename = file.filename or "upload"
    document_title = (title or "").strip() or filename

    content_bytes = await file.read()
    if len(content_bytes) > settings.KB_MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {settings.KB_MAX_FILE_BYTES // (1024 * 1024)} MB)",
        )
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Quick validation extract (full pipeline runs in background)
    try:
        extracted = extract_document(content_bytes, filename, file.content_type)
    except DocumentExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    text_hash = content_hash(extracted.text)
    if not allow_duplicate:
        dup = await find_duplicate_by_hash(text_hash)
        if dup:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Duplicate document content",
                    "existing_document_id": dup.get("id"),
                    "existing_title": dup.get("title"),
                },
            )

    job_info = await create_ingest_job(
        title=document_title,
        filename=filename,
        file_type=file.content_type,
        file_size=len(content_bytes),
        uploaded_by=user_id,
        category=category,
    )

    background_tasks.add_task(
        run_ingest_pipeline,
        document_id=job_info["document_id"],
        job_id=job_info["job_id"],
        content_bytes=content_bytes,
        filename=filename,
        title=document_title,
        file_type=file.content_type,
        uploaded_by=user_id,
        category=category,
        allow_duplicate=allow_duplicate,
    )

    logger.info(
        "Queued ingest document_id=%s job_id=%s user=%s file=%s",
        job_info["document_id"],
        job_info["job_id"],
        user_id,
        filename,
    )

    return {
        "status": "accepted",
        "message": "Document ingestion queued",
        "document_id": job_info["document_id"],
        "job_id": job_info["job_id"],
        "filename": filename,
    }
