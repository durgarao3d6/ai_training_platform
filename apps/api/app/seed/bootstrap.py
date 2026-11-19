"""Bootstrap: the only seeded data (product decision, 8 Nov 2026).

  python -m app.seed.bootstrap

Creates:
- the four role profiles (from code; their checkers are code plugins),
- the object storage bucket,
- seven user accounts so every role can sign in: one intern per track, a trainer, HR and an admin.

Nothing else is seeded. Courses, milestones, tasks, rubrics, cohorts, enrollments and progress are
created in the application (or once with `python -m app.content.cli import`). No scores, findings,
evidence or decisions are ever written here. Running it twice changes nothing.

Runs as the table owner (MIGRATION_DATABASE_URL). Requires DEMO_PASSWORD (12+ characters) for the
seeded accounts.
"""

import os
import sys
from dataclasses import dataclass

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.storage import ensure_bucket
from app.modules.catalog.roles import ensure_role_profiles
from app.modules.identity.models import Role, RoleAssignment, User
from app.modules.identity.security import hash_password, verify_password

MIN_PASSWORD = 12


@dataclass(frozen=True)
class SeedUser:
    email: str
    full_name: str
    role: Role


# Placeholder identities (no real people). Rename them in the app if you like; the seed only
# creates missing accounts and never overwrites names changed later.
SEED_USERS = [
    SeedUser("intern.dev@example.com", "Developer Intern 01", Role.intern),
    SeedUser("intern.ba@example.com", "Business Analyst Intern 01", Role.intern),
    SeedUser("intern.qa@example.com", "QA Intern 01", Role.intern),
    SeedUser("intern.ux@example.com", "UI/UX Intern 01", Role.intern),
    SeedUser("trainer@example.com", "Trainer 01", Role.trainer),
    SeedUser("hr@example.com", "HR Manager 01", Role.hr),
    SeedUser("admin@example.com", "Administrator", Role.admin),
]


def seed_users(db: Session, password: str) -> tuple[int, int]:
    """Returns (accounts created, accounts updated)."""
    created = updated = 0
    for seed in SEED_USERS:
        user = db.scalar(select(User).where(User.email == seed.email))
        if user is None:
            user = User(
                email=seed.email, full_name=seed.full_name, password_hash=hash_password(password)
            )
            db.add(user)
            db.flush()
            created += 1
        elif not verify_password(user.password_hash, password):
            # Argon2 hashes are salted; only rehash when DEMO_PASSWORD actually changed.
            user.password_hash = hash_password(password)
            updated += 1
        if (
            db.scalar(
                select(RoleAssignment).where(
                    RoleAssignment.user_id == user.id, RoleAssignment.role == seed.role
                )
            )
            is None
        ):
            db.add(RoleAssignment(user_id=user.id, role=seed.role))
    db.flush()
    return created, updated


def main() -> int:
    password = os.environ.get("DEMO_PASSWORD", "")
    if len(password) < MIN_PASSWORD:
        print(f"Set DEMO_PASSWORD (at least {MIN_PASSWORD} characters) in .env before seeding.")
        return 1
    ensure_bucket()
    engine = create_engine(get_settings().migration_database_url)
    with Session(engine) as db, db.begin():
        ensure_role_profiles(db)
        created, updated = seed_users(db, password)
    print(f"Bootstrap done. Accounts created: {created}. Passwords updated: {updated}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
