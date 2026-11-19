"""Imports every model so Base.metadata is complete (used by Alembic and tests)."""

from app.db import outbox as _outbox
from app.modules.audit import models as _audit
from app.modules.authoring import models as _authoring
from app.modules.catalog import models as _catalog
from app.modules.competency import models as _competency
from app.modules.delivery import models as _delivery
from app.modules.evaluation import models as _evaluation
from app.modules.identity import models as _identity
from app.modules.llm_gateway import models as _llm_gateway
from app.modules.progression import models as _progression
from app.modules.review import models as _review
from app.modules.submissions import models as _submissions
from app.modules.traceability import models as _traceability

__all__ = [
    "_outbox",
    "_audit",
    "_authoring",
    "_catalog",
    "_competency",
    "_delivery",
    "_evaluation",
    "_identity",
    "_llm_gateway",
    "_progression",
    "_review",
    "_submissions",
    "_traceability",
]
