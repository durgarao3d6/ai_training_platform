"""FR-IAM-02: trainer review routes use the existing submission-review permission."""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.identity.deps import Principal, get_principal

ID = uuid.uuid4()
ROOT = "/api/v1/trainer"


@pytest.mark.parametrize(
    "role,status", [(None, 401), ("intern", 403), ("hr", 403), ("admin", 403), ("trainer", 200)]
)
def test_review_queue_permission(role: str | None, status: int) -> None:
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    if role is not None:
        app.dependency_overrides[get_principal] = lambda: Principal(ID, frozenset({role}))
    try:
        client = TestClient(app)
        assert client.get(f"{ROOT}/review-queue").status_code == status
        db.execute.return_value.one_or_none.return_value = None
        attempt_status = 404 if role == "trainer" else status
        assert client.get(f"{ROOT}/submissions/{ID}/rubric").status_code == attempt_status
        assert (
            client.post(
                f"{ROOT}/submissions/{ID}/decision",
                json={"decision": "approve", "reason": "", "rubric_version_id": str(ID)},
            ).status_code
            == attempt_status
        )
    finally:
        app.dependency_overrides.clear()
