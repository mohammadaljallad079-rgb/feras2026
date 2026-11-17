"""Authenticated file upload and download. No public direct storage path."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import assert_company_access, get_current_user, require
from app.core.db import get_db
from app.models.identity import User
from app.models.operations import StoredFile
from app.schemas import FileOut
from app.services import audit
from app.services.files import path_for, save_upload

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    company_id: int | None = Form(default=None),
    is_confidential: bool = Form(default=False),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileOut:
    if company_id is not None:
        assert_company_access(db, actor, company_id)
    record = await save_upload(
        db, file, owner_id=actor.id, company_id=company_id, is_confidential=is_confidential
    )
    audit.record(db, action="file.upload", actor=actor, target_type="file", target_id=record.id, company_id=company_id)
    db.commit()
    db.refresh(record)
    return FileOut.model_validate(record)


@router.get("/{file_id}/download")
def download(
    file_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    record = db.get(StoredFile, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    if record.company_id is not None:
        assert_company_access(db, actor, record.company_id)
    # Confidential HR files require an explicit permission, otherwise the UI is
    # shown "مرفق مقيد" and this endpoint refuses.
    if record.is_confidential and "hr:view_confidential" not in _perms(actor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "restricted_attachment"})
    path = path_for(record)
    audit.record(db, action="file.download", actor=actor, target_type="file", target_id=record.id, company_id=record.company_id)
    db.commit()
    return FileResponse(
        path,
        media_type=record.content_type,
        filename=record.original_name,
        content_disposition_type="attachment",
    )


def _perms(user: User) -> set[str]:
    out: set[str] = set()
    for ur in user.roles:
        if ur.role:
            out |= ur.role.permission_codes
    return out
