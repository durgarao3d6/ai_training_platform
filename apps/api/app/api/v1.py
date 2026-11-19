"""Version 1 API router. Module routers are mounted here as they are built."""

from fastapi import APIRouter

from app.api.pagination import Page
from app.modules.admin.router import router as admin_router
from app.modules.authoring.router import router as authoring_router
from app.modules.authoring.router import study_router
from app.modules.catalog.router import router as catalog_router
from app.modules.delivery.router import router as delivery_router
from app.modules.identity.router import router as identity_router
from app.modules.progression.router import router as progression_router
from app.modules.submissions.router import router as submissions_router

__all__ = ["Page", "router"]

router = APIRouter(prefix="/api/v1")
router.include_router(identity_router)
router.include_router(catalog_router)
router.include_router(delivery_router)
router.include_router(progression_router)
router.include_router(submissions_router)
router.include_router(admin_router)
router.include_router(authoring_router)
router.include_router(study_router)
