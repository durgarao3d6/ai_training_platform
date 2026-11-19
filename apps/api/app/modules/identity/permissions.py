"""Permission matrix (Architecture 13.2). Human review required (tech lead).

Role checks happen here. Row scoping ("own", "assigned only") is enforced by PostgreSQL
row-level security (app/db/rls.py), so both layers must agree.
"""

from enum import Enum

from app.modules.identity.models import Role


class Permission(str, Enum):
    SUBMISSION_READ_OWN = "submission.read_own"
    SUBMISSION_CREATE_OWN = "submission.create_own"
    SUBMISSION_READ_ASSIGNED = "submission.read_assigned"
    SUBMISSION_REVIEW = "submission.review"
    SUBMISSION_READ_ALL = "submission.read_all"
    COHORT_OVERVIEW = "cohort.overview"
    DECISION_OVERRIDE = "decision.override"  # reason required, enforced in the review service
    RUBRIC_READ_PUBLISHED = "rubric.read_published"
    RUBRIC_READ = "rubric.read"
    RUBRIC_DRAFT = "rubric.draft"
    RUBRIC_PUBLISH = "rubric.publish"
    USERS_MANAGE_INTERNS = "users.manage_interns"
    USERS_MANAGE_ALL = "users.manage_all"
    AUDIT_READ = "audit.read"
    CATALOG_MANAGE = "catalog.manage"  # author courses, milestones and tasks in the app
    COHORT_MANAGE = "cohort.manage"  # create cohorts and enroll interns
    # Use AI authoring assistance and edit one's own drafts. Never publishes or approves.
    CATALOG_DRAFT = "catalog.draft"


P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.intern: frozenset(
        {P.SUBMISSION_READ_OWN, P.SUBMISSION_CREATE_OWN, P.RUBRIC_READ_PUBLISHED}
    ),
    Role.trainer: frozenset(
        {
            P.SUBMISSION_READ_ASSIGNED,
            P.SUBMISSION_REVIEW,
            P.COHORT_OVERVIEW,
            P.DECISION_OVERRIDE,
            P.RUBRIC_READ_PUBLISHED,
            P.RUBRIC_READ,
            P.CATALOG_DRAFT,
        }
    ),
    Role.hr: frozenset(
        {
            P.COHORT_OVERVIEW,
            P.RUBRIC_READ_PUBLISHED,
            P.RUBRIC_READ,
            P.USERS_MANAGE_INTERNS,
            P.COHORT_MANAGE,
        }
    ),
    Role.admin: frozenset(
        {
            P.SUBMISSION_READ_ALL,
            P.COHORT_OVERVIEW,
            P.DECISION_OVERRIDE,
            P.RUBRIC_READ_PUBLISHED,
            P.RUBRIC_READ,
            P.RUBRIC_DRAFT,
            P.RUBRIC_PUBLISH,
            P.USERS_MANAGE_INTERNS,
            P.USERS_MANAGE_ALL,
            P.AUDIT_READ,
            P.CATALOG_MANAGE,
            P.COHORT_MANAGE,
            P.CATALOG_DRAFT,
        }
    ),
}


def permissions_for(roles: frozenset[str]) -> frozenset[Permission]:
    granted: set[Permission] = set()
    for name in roles:
        try:
            granted |= ROLE_PERMISSIONS[Role(name)]
        except ValueError:
            continue  # unknown role names grant nothing
    return frozenset(granted)


def has_any(roles: frozenset[str], *required: Permission) -> bool:
    return bool(permissions_for(roles) & set(required))
