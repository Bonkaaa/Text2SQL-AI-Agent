"""Gói định tuyến API (API Routers)."""

from src.api.routes.audit import router as audit_router
from src.api.routes.query import router as query_router

__all__ = [
    "audit_router",
    "query_router",
]
