"""
Document Ingestion API Endpoint (Admin only)
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from typing import Optional
from app.core.auth import require_ai_assistant_access
from app.core.audit import log_audit
from app.services.vector_store import ingest_document
from app.utils.logger import get_logger
import io

logger = get_logger(__name__)
router = APIRouter()


@router.post("/ingest")
async def ingest_document_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: dict = Depends(require_ai_assistant_access)
):
    """
    Ingest document into knowledge base
    (Same role gate as other AI Assistant APIs.)
    
    Supports: .txt, .md, .pdf (text extraction)
    """
    try:
        user_id = current_user.get("id")
        logger.info(f"Document ingestion request from user {user_id}: {file.filename}")
        
        # Read file content
        content_bytes = await file.read()
        
        # Extract text based on file type
        content = extract_text_from_file(content_bytes, file.content_type or file.filename)
        
        if not content:
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        
        # Use filename as title if not provided
        document_title = title or file.filename or "Untitled Document"
        
        # Ingest document
        document_id = await ingest_document(
            title=document_title,
            content=content,
            file_path=file.filename,
            file_type=file.content_type,
            uploaded_by=user_id
        )
        
        # Log ingestion
        await log_audit(
            user_id=user_id,
            action="document_ingest",
            resource="kb_documents",
            request_data={
                "filename": file.filename,
                "content_type": file.content_type,
                "document_id": document_id
            }
        )
        
        return {
            "status": "success",
            "message": "Document ingested successfully",
            "document_id": document_id,
            "filename": file.filename
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def extract_text_from_file(content_bytes: bytes, content_type: str) -> str:
    """
    Extract text from file based on content type
    """
    try:
        # Text files
        if content_type in ["text/plain", "text/markdown"] or content_type.endswith(".txt") or content_type.endswith(".md"):
            return content_bytes.decode("utf-8")
        
        # Markdown
        if content_type == "text/markdown" or content_type.endswith(".md"):
            return content_bytes.decode("utf-8")
        
        # Default: try UTF-8
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Try other encodings
            for encoding in ["latin-1", "cp1252"]:
                try:
                    return content_bytes.decode(encoding)
                except UnicodeDecodeError:
                    continue
        
        raise Exception("Could not decode file content")
    
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        raise
