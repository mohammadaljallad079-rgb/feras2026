"""Aggregate API v1 router."""

from fastapi import APIRouter

from app.api.v1 import (
    accounting,
    advisor,
    ai,
    audit,
    auth,
    companies,
    crm,
    dashboard,
    directives,
    files,
    forms,
    hr,
    public,
    reporting,
    service_requests,
    users,
    website,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(companies.router)
api_router.include_router(files.router)
api_router.include_router(reporting.router)
api_router.include_router(forms.router)
api_router.include_router(accounting.router)
api_router.include_router(service_requests.router)
api_router.include_router(crm.router)
api_router.include_router(directives.router)
api_router.include_router(hr.router)
api_router.include_router(website.router)
api_router.include_router(advisor.router)
api_router.include_router(ai.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)

public_router = APIRouter(prefix="/api/v1")
public_router.include_router(public.router)
