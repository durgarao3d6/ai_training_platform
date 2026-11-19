"""Authorisation and payload rules for AI-assisted authoring (AGENTS.md rule 7, open questions 7).

Authorisation tests use a mock database. They prove the permission layer: a denied role gets 403
before any handler code runs; an allowed role gets anything except 401 or 403 (the handler may then
return 404, 422 or even 500 against the mock, which still shows authorisation passed).
Database behaviour (draft modules hidden from interns, approval publishing) is NOT covered here and
needs an integration test with PostgreSQL.
"""

import uuid
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.modules.authoring import schemas as s
from app.modules.identity.deps import Principal, get_principal

ID = uuid.uuid4()
P = "/api/v1/authoring"

# (method, path) endpoints open to trainer and admin.
DRAFT_ENDPOINTS = [
    ("GET", f"{P}/config"),
    ("GET", f"{P}/courses"),
    ("GET", f"{P}/courses/{ID}"),
    ("POST", f"{P}/courses"),
    ("PATCH", f"{P}/modules/{ID}"),
    ("PATCH", f"{P}/tasks/{ID}"),
    ("POST", f"{P}/drafts"),
    ("POST", f"{P}/attach"),
    ("POST", f"{P}/materials/{ID}/improve"),
    ("GET", f"{P}/jobs/{ID}"),
    ("POST", f"{P}/jobs/{ID}/accept"),
    ("POST", f"{P}/jobs/{ID}/dismiss"),
    ("POST", f"{P}/materials"),
    ("GET", f"{P}/materials"),
    ("POST", f"{P}/materials/{ID}/publish"),
    ("GET", f"{P}/components"),
    ("POST", f"{P}/components"),
    ("PATCH", f"{P}/components/{ID}"),
    ("DELETE", f"{P}/components/{ID}"),
    ("POST", f"{P}/components/{ID}/submit"),
    ("POST", f"{P}/components/{ID}/verify-link"),
]
# Approval is admin only.
ADMIN_ONLY = [
    ("GET", f"{P}/pending"),
    ("POST", f"{P}/modules/{ID}/approve"),
    ("POST", f"{P}/components/{ID}/approve"),
]


def _make_client(monkeypatch: pytest.MonkeyPatch, ai_enabled: bool) -> TestClient:
    monkeypatch.setenv("AI_AUTHORING_ENABLED", "true" if ai_enabled else "false")
    get_settings.cache_clear()
    db = MagicMock()
    db.get.return_value = None
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield _make_client(monkeypatch, ai_enabled=True)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def client_ai_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield _make_client(monkeypatch, ai_enabled=False)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _as(role: str | None) -> None:
    if role is None:
        app.dependency_overrides.pop(get_principal, None)
    else:
        app.dependency_overrides[get_principal] = lambda: Principal(uuid.uuid4(), frozenset({role}))


@pytest.mark.parametrize(("method", "path"), DRAFT_ENDPOINTS + ADMIN_ONLY)
def test_unauthenticated_is_rejected(client: TestClient, method: str, path: str) -> None:
    _as(None)
    assert client.request(method, path, json={}).status_code == 401


@pytest.mark.parametrize("role", ["intern", "hr"])
@pytest.mark.parametrize(("method", "path"), DRAFT_ENDPOINTS + ADMIN_ONLY)
def test_intern_and_hr_are_denied(client: TestClient, method: str, path: str, role: str) -> None:
    _as(role)
    assert client.request(method, path, json={}).status_code == 403


@pytest.mark.parametrize("role", ["trainer", "admin"])
@pytest.mark.parametrize(("method", "path"), DRAFT_ENDPOINTS)
def test_trainer_and_admin_pass_authorisation(
    client: TestClient, method: str, path: str, role: str
) -> None:
    _as(role)
    assert client.request(method, path, json={}).status_code not in (401, 403)


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY)
def test_trainer_cannot_approve(client: TestClient, method: str, path: str) -> None:
    _as("trainer")
    assert client.request(method, path, json={}).status_code == 403


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY)
def test_admin_can_approve(client: TestClient, method: str, path: str) -> None:
    _as("admin")
    assert client.request(method, path, json={}).status_code not in (401, 403)


@pytest.mark.parametrize("path", [f"{P}/drafts", f"{P}/attach", f"{P}/materials/{ID}/improve"])
def test_ai_endpoints_return_404_when_flag_is_off(client_ai_off: TestClient, path: str) -> None:
    _as("admin")
    assert client_ai_off.post(path, json={}).status_code == 404


# ---------- Payload rules ----------


def test_resource_must_be_https_and_starts_unverified() -> None:
    assert s.validate_payload("resource", {"url": "http://example.com"}) is None
    ok = s.validate_payload("resource", {"url": "https://example.com/docs", "note": "n"})
    assert ok is not None and ok["link_verified"] is False


def test_resource_cannot_claim_to_be_verified() -> None:
    ok = s.validate_payload("resource", {"url": "https://example.com", "link_verified": True})
    assert ok is not None and ok["link_verified"] is False


def test_quiz_correct_index_must_exist() -> None:
    bad = {"questions": [{"question": "q", "options": ["a", "b"], "correct_index": 3}]}
    good = {"questions": [{"question": "q", "options": ["a", "b"], "correct_index": 1}]}
    assert s.validate_payload("quiz", bad) is None
    assert s.validate_payload("quiz", good) is not None


def test_starter_filename_cannot_escape_a_folder() -> None:
    assert s.validate_payload("starter_file", {"filename": "../../etc/passwd"}) is None
    assert s.validate_payload("starter_file", {"filename": "chunker.py"}) is not None


def test_rubric_is_not_an_attachable_type() -> None:
    assert s.validate_payload("rubric_draft", {}) is None
    assert s.validate_payload("unknown", {}) is None


# ---------- Learner study material ----------

STUDY = f"/api/v1/modules/{ID}/study"


def test_study_requires_sign_in(client: TestClient) -> None:
    _as(None)
    assert client.get(STUDY).status_code == 401


@pytest.mark.parametrize("role", ["intern", "trainer", "hr", "admin"])
def test_study_open_to_every_platform_role(client: TestClient, role: str) -> None:
    _as(role)
    assert client.get(STUDY).status_code not in (401, 403)  # 404 here: the mock has no milestone


def test_study_denied_for_unknown_role(client: TestClient) -> None:
    _as("guest")
    assert client.get(STUDY).status_code == 403
