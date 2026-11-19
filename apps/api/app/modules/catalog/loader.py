"""One-time import of drafted content files into the catalog (product decision, 8 Nov 2026).

Course content lives in the database and is authored in the application. The YAML drafted in
content/ (Milestone Catalog draft) can be imported once so the role experts' work is not lost.

- Create-only: a course, milestone or task whose key already exists is skipped, never
  overwritten, so re-running the import cannot undo edits made in the app.
- Rubric files in content/rubrics/ are imported as published versions, matched by content hash.
- Role profiles come from code (catalog/roles.py), not from files.
Must run as the table owner (migration database URL).
"""

from dataclasses import dataclass, field
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.content import (
    DEFAULT_DELIVERABLES,
    ContentBundle,
    ContentError,
    rubric_hash,
)
from app.modules.catalog.models import (
    Course,
    Module,
    RubricVersion,
    TaskDepth,
    TaskTemplate,
    TaskType,
)
from app.modules.catalog.roles import ensure_role_profiles

M = TypeVar("M", Course, Module, TaskTemplate)


@dataclass
class ImportSummary:
    created: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)

    def bump(self, kind: str, table: str) -> None:
        bucket = self.created if kind == "created" else self.skipped
        bucket[table] = bucket.get(table, 0) + 1

    @property
    def changed(self) -> bool:
        return bool(self.created)


def _create_if_missing(
    db: Session, model: type[M], key: str, values: dict[str, Any], summary: ImportSummary
) -> M:
    row = db.scalar(select(model).where(model.key == key))
    if row is not None:
        summary.bump("skipped", model.__tablename__)
        return row
    row = model(key=key, **values)
    db.add(row)
    db.flush()
    summary.bump("created", model.__tablename__)
    return row


def _import_rubric(db: Session, doc: dict[str, Any], summary: ImportSummary) -> RubricVersion:
    digest = rubric_hash(doc)
    existing = db.scalar(select(RubricVersion).where(RubricVersion.content_hash == digest))
    if existing is not None:
        summary.bump("skipped", RubricVersion.__tablename__)
        return existing
    clash = db.scalar(
        select(RubricVersion).where(
            RubricVersion.rubric_key == doc["rubric_id"], RubricVersion.version == doc["version"]
        )
    )
    if clash is not None:
        raise ContentError(
            [
                f"rubric '{doc['rubric_id']}' version {doc['version']} already exists with different content"
            ]
        )
    row = RubricVersion(
        rubric_key=doc["rubric_id"],
        version=doc["version"],
        content_hash=digest,
        content=doc,
        published=True,
    )
    db.add(row)
    db.flush()
    summary.bump("created", RubricVersion.__tablename__)
    return row


def import_bundle(db: Session, bundle: ContentBundle) -> ImportSummary:
    summary = ImportSummary()
    roles = ensure_role_profiles(db)

    modules: dict[str, Module] = {}
    for key, course in bundle.courses.items():
        course_row = _create_if_missing(
            db,
            Course,
            key,
            {
                "role_profile_id": roles[course.role_profile].id,
                "title": course.title,
                "description": course.description,
                "review_status": course.review_status,
                "final_deliverable": course.final_deliverable,
            },
            summary,
        )
        for m in course.milestones:
            modules[m.key] = _create_if_missing(
                db,
                Module,
                m.key,
                {
                    "course_id": course_row.id,
                    "title": m.title,
                    "position": m.position,
                    "description": m.description,
                    "learning_objective": m.learning_objective,
                },
                summary,
            )

    rubrics = {rid: _import_rubric(db, doc, summary) for rid, doc in bundle.rubrics.items()}

    for key, task in bundle.tasks.items():
        rubric = rubrics.get(task["rubric"]) if task.get("rubric") else None
        _create_if_missing(
            db,
            TaskTemplate,
            key,
            {
                "module_id": modules[task["module"]].id,
                "title": task["title"],
                "task_type": TaskType(task["task_type"]),
                "description": task["description"],
                "learning_objective": task.get("learning_objective", ""),
                # One manifest per task: its own, else its rubric's, else the generic one.
                "deliverables": task.get("deliverables")
                or (rubric.content.get("deliverables") if rubric else None)
                or DEFAULT_DELIVERABLES,
                "depth": TaskDepth(task["depth"]),
                "rubric_version_id": rubric.id if rubric else None,
                "submits": task.get("submits", ""),
                "evaluated_on": task.get("evaluated_on", ""),
                "requires_review": task.get("requires_review", False),
                "starter_files": task.get("starter_files", []),
            },
            summary,
        )

    return summary
