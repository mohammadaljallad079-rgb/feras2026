"""Employees and HR records, including confidential attachment handling."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, require
from app.core.db import get_db
from app.models.enums import EmployeeStatus
from app.models.identity import User
from app.models.operations import Employee, EmployeeEvent, StoredFile
from app.schemas import (
    EmployeeCreate,
    EmployeeEventCreate,
    EmployeeEventOut,
    EmployeeOut,
    EmployeeUpdate,
)
from app.services import audit

router = APIRouter(prefix="/employees", tags=["hr"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(
    company_id: int | None = None,
    employee_status: str | None = None,
    user: User = Depends(require("hr:view")),
    db: Session = Depends(get_db),
) -> list[EmployeeOut]:
    stmt = select(Employee)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(Employee.company_id.in_(allowed or {-1}))
    if company_id:
        assert_company_access(db, user, company_id)
        stmt = stmt.where(Employee.company_id == company_id)
    if employee_status:
        stmt = stmt.where(Employee.status == employee_status)
    rows = db.execute(stmt.order_by(Employee.id.desc())).scalars().all()
    return [EmployeeOut.model_validate(e) for e in rows]


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    actor: User = Depends(require("hr:manage")),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    assert_company_access(db, actor, payload.company_id)
    emp = Employee(**payload.model_dump())
    db.add(emp)
    db.flush()
    audit.record(db, action="employee.create", actor=actor, target_type="employee", target_id=emp.id, company_id=emp.company_id)
    db.commit()
    db.refresh(emp)
    return EmployeeOut.model_validate(emp)


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    actor: User = Depends(require("hr:manage")),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    assert_company_access(db, actor, emp.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in {s.value for s in EmployeeStatus}:
        raise HTTPException(status_code=422, detail="Unknown status")
    for key, value in changes.items():
        setattr(emp, key, value)
    audit.record(db, action="employee.update", actor=actor, target_type="employee", target_id=emp.id, company_id=emp.company_id)
    db.commit()
    db.refresh(emp)
    return EmployeeOut.model_validate(emp)


@router.get("/{employee_id}/events", response_model=list[EmployeeEventOut])
def list_events(
    employee_id: int,
    actor: User = Depends(require("hr:view")),
    db: Session = Depends(get_db),
) -> list[EmployeeEventOut]:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    assert_company_access(db, actor, emp.company_id)
    rows = db.execute(
        select(EmployeeEvent).where(EmployeeEvent.employee_id == employee_id).order_by(EmployeeEvent.id.desc())
    ).scalars().all()
    return [EmployeeEventOut.model_validate(e) for e in rows]


@router.post("/{employee_id}/events", response_model=EmployeeEventOut, status_code=status.HTTP_201_CREATED)
def add_event(
    employee_id: int,
    payload: EmployeeEventCreate,
    actor: User = Depends(require("hr:manage")),
    db: Session = Depends(get_db),
) -> EmployeeEventOut:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    assert_company_access(db, actor, emp.company_id)
    if payload.attachment_file_id is not None:
        f = db.get(StoredFile, payload.attachment_file_id)
        if f is None:
            raise HTTPException(status_code=422, detail="Attachment not found")
    event = EmployeeEvent(employee_id=employee_id, **payload.model_dump())
    db.add(event)
    audit.record(db, action="employee.event.create", actor=actor, target_type="employee", target_id=emp.id, company_id=emp.company_id)
    db.commit()
    db.refresh(event)
    return EmployeeEventOut.model_validate(event)
