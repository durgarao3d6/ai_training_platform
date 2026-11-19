"""The four role profiles (Architecture 10).

Role profiles stay in code because their checkers are code plugins: adding a role means adding
checkers. Everything else in the catalog (courses, milestones, tasks, deliverables, rubrics) is
authored in the application. `ensure_role_profiles` keeps the table in step with this file.
"""

import json
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.validator import find_contracts_dir
from app.modules.catalog.models import RoleProfile

ROLE_PROFILES: dict[str, dict[str, Any]] = {
    "developer": {"name": "Software Developer", "review_policy": {"always_review": False}},
    "ba": {"name": "Business Analyst", "review_policy": {"always_review": False}},
    "qa": {"name": "QA Engineer", "review_policy": {"always_review": False}},
    # UI/UX work is always reviewed by a trainer (Architecture 8.6).
    "uiux": {"name": "UI/UX Designer", "review_policy": {"always_review": True}},
}


def checker_registry() -> dict[str, list[str]]:
    """Registered checker keys per role (packages/contracts/checkers.json)."""
    return cast(
        dict[str, list[str]],
        json.loads((find_contracts_dir() / "checkers.json").read_text(encoding="utf-8")),
    )


def ensure_role_profiles(db: Session) -> dict[str, RoleProfile]:
    """Create or update the four role profiles. Judge prompts are set when prompts exist (Phase 4)."""
    registry = checker_registry()
    rows: dict[str, RoleProfile] = {}
    for key, spec in ROLE_PROFILES.items():
        row = db.scalar(select(RoleProfile).where(RoleProfile.key == key))
        values = {
            "name": spec["name"],
            "checker_keys": registry.get(key, []),
            "review_policy": spec["review_policy"],
        }
        if row is None:
            row = RoleProfile(key=key, **values)
            db.add(row)
        else:
            for name, value in values.items():
                if getattr(row, name) != value:
                    setattr(row, name, value)
        rows[key] = row
    db.flush()
    return rows
