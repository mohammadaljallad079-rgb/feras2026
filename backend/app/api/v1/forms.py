"""Dynamic form builder. Definition changes bump the version and never mutate
historical report values (which store the version they were captured under)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.db import get_db
from app.models.business import FormField
from app.models.enums import FieldType
from app.models.identity import User
from app.schemas import FormFieldCreate, FormFieldOut, FormFieldUpdate
from app.services import audit

router = APIRouter(prefix="/form-fields", tags=["forms"])


@router.get("", response_model=list[FormFieldOut])
def list_fields(
    include_inactive: bool = False,
    _: User = Depends(require("report:view_own")),
    db: Session = Depends(get_db),
) -> list[FormFieldOut]:
    stmt = select(FormField).order_by(FormField.display_order, FormField.id)
    if not include_inactive:
        stmt = stmt.where(FormField.is_active.is_(True))
    return [FormFieldOut.model_validate(f) for f in db.execute(stmt).scalars().all()]


@router.post("", response_model=FormFieldOut, status_code=status.HTTP_201_CREATED)
def create_field(
    payload: FormFieldCreate,
    actor: User = Depends(require("form:manage")),
    db: Session = Depends(get_db),
) -> FormFieldOut:
    if payload.field_type not in {t.value for t in FieldType}:
        raise HTTPException(status_code=422, detail="Unknown field type")
    if payload.parent_id is not None and db.get(FormField, payload.parent_id) is None:
        raise HTTPException(status_code=422, detail="Parent field not found")
    field = FormField(**payload.model_dump(), version=1)
    db.add(field)
    db.flush()
    audit.record(db, action="form_field.create", actor=actor, target_type="form_field", target_id=field.id)
    db.commit()
    db.refresh(field)
    return FormFieldOut.model_validate(field)


@router.patch("/{field_id}", response_model=FormFieldOut)
def update_field(
    field_id: int,
    payload: FormFieldUpdate,
    actor: User = Depends(require("form:manage")),
    db: Session = Depends(get_db),
) -> FormFieldOut:
    field = db.get(FormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(field, key, value)
    if changes:
        field.version += 1
    audit.record(db, action="form_field.update", actor=actor, target_type="form_field", target_id=field.id)
    db.commit()
    db.refresh(field)
    return FormFieldOut.model_validate(field)


@router.post("/{field_id}/deactivate", response_model=FormFieldOut)
def deactivate_field(
    field_id: int,
    actor: User = Depends(require("form:manage")),
    db: Session = Depends(get_db),
) -> FormFieldOut:
    field = db.get(FormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    field.is_active = False
    field.version += 1
    audit.record(db, action="form_field.deactivate", actor=actor, target_type="form_field", target_id=field.id)
    db.commit()
    db.refresh(field)
    return FormFieldOut.model_validate(field)
