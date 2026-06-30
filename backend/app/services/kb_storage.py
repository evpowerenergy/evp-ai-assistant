"""
Supabase Storage helpers for knowledge-base originals.
"""
from __future__ import annotations

import re
from typing import Optional

from app.config import settings
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_filename(filename: str) -> str:
    name = (filename or "upload").strip()
    name = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE)
    return name[:200] or "upload"


def storage_path_for(document_id: str, filename: str) -> str:
    return f"{document_id}/{_sanitize_filename(filename)}"


def upload_original(document_id: str, filename: str, content_bytes: bytes) -> str:
    bucket = settings.KB_STORAGE_BUCKET
    path = storage_path_for(document_id, filename)
    supabase = get_supabase_client()
    supabase.storage.from_(bucket).upload(
        path,
        content_bytes,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )
    logger.info("Uploaded KB original: bucket=%s path=%s bytes=%s", bucket, path, len(content_bytes))
    return path


def delete_original(storage_path: Optional[str], bucket: Optional[str] = None) -> None:
    if not storage_path:
        return
    bucket = bucket or settings.KB_STORAGE_BUCKET
    try:
        supabase = get_supabase_client()
        supabase.storage.from_(bucket).remove([storage_path])
        logger.info("Deleted KB original: %s", storage_path)
    except Exception as e:
        logger.warning("Failed to delete storage object %s: %s", storage_path, e)


def create_signed_download_url(
    storage_path: str,
    bucket: Optional[str] = None,
    expires_sec: int = 3600,
) -> str:
    bucket = bucket or settings.KB_STORAGE_BUCKET
    supabase = get_supabase_client()
    result = supabase.storage.from_(bucket).create_signed_url(storage_path, expires_sec)
    if isinstance(result, dict):
        url = result.get("signedURL") or result.get("signedUrl")
        if url:
            return url
    signed = getattr(result, "data", None) or {}
    if isinstance(signed, dict):
        return signed.get("signedURL") or signed.get("signedUrl") or ""
    raise RuntimeError("Could not create signed download URL")


def download_original(storage_path: str, bucket: Optional[str] = None) -> bytes:
    bucket = bucket or settings.KB_STORAGE_BUCKET
    supabase = get_supabase_client()
    return supabase.storage.from_(bucket).download(storage_path)
