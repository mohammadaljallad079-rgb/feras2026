"""Private file storage with validation and randomized storage names."""

from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.operations import StoredFile

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/csv",
    "text/plain",
}


def _storage_root() -> Path:
    root = Path(settings.storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload(
    db: Session,
    upload: UploadFile,
    *,
    owner_id: int | None,
    company_id: int | None,
    is_confidential: bool = False,
) -> StoredFile:
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "unsupported_type", "content_type": upload.content_type},
        )
    data = await upload.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "file_too_large", "max_bytes": settings.max_upload_bytes},
        )
    storage_name = f"{secrets.token_hex(16)}"
    dest = _storage_root() / storage_name
    dest.write_bytes(data)

    record = StoredFile(
        storage_name=storage_name,
        original_name=os.path.basename(upload.filename or "upload"),
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=len(data),
        checksum=hashlib.sha256(data).hexdigest(),
        owner_id=owner_id,
        company_id=company_id,
        is_confidential=is_confidential,
    )
    db.add(record)
    db.flush()
    return record


def path_for(record: StoredFile) -> Path:
    path = _storage_root() / record.storage_name
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing")
    return path
