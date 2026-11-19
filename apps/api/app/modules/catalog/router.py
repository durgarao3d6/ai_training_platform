"""Catalog read endpoints (Architecture 14). Any signed-in role may read the catalog."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.pagination import Page
from app.modules.catalog import service
from app.modules.catalog.schemas import CourseOut, ModuleOut
from app.modules.identity.deps import get_scoped_db

router = APIRouter(tags=["catalog"])


@router.get("/courses", response_model=Page[CourseOut])
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_scoped_db),
) -> Page[CourseOut]:
    items, total = service.list_courses(db, page, page_size)
    return Page[CourseOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/courses/{course_id}/modules", response_model=list[ModuleOut])
def list_modules(course_id: uuid.UUID, db: Session = Depends(get_scoped_db)) -> list[ModuleOut]:
    if not service.course_exists(db, course_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    return service.list_modules(db, course_id)
