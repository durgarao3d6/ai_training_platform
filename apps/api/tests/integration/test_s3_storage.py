"""S3 operations AITMS uses, against the local RustFS service (ADR-011 condition 5, AITMS-TECH-002).

Run with: scripts/dev.ps1 test-integration   (sets RUN_INTEGRATION=1 inside the tools container)
"""

import hashlib
import os
import uuid
from collections.abc import Iterator

import httpx
import pytest

from app.core import storage
from app.core.config import get_settings
from app.modules.delivery.models import TaskInstance
from app.modules.submissions.schemas import ArtifactIn
from app.modules.submissions.service import _validate

pytestmark = pytest.mark.skipif(os.environ.get("RUN_INTEGRATION") != "1", reason="integration test")

PAYLOAD = "Smart Knowledge Portal ✓ chunk 1\n".encode() * 64
CONTENT_TYPE = "text/markdown"


@pytest.fixture(autouse=True)
def isolated_bucket(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Each run uses its own bucket so the test never touches real submissions."""
    monkeypatch.setenv("S3_BUCKET", f"aitms-it-{uuid.uuid4().hex[:12]}")
    get_settings.cache_clear()
    storage.get_client.cache_clear()
    storage.ensure_bucket()
    yield
    client, bucket = storage.get_client(), get_settings().s3_bucket
    for item in client.list_objects_v2(Bucket=bucket).get("Contents", []):
        client.delete_object(Bucket=bucket, Key=item["Key"])
    client.delete_bucket(Bucket=bucket)
    get_settings.cache_clear()
    storage.get_client.cache_clear()


def _post(
    key: str, data: bytes, content_type: str = CONTENT_TYPE, max_bytes: int = 1024 * 1024
) -> httpx.Response:
    signed = storage.presign_upload(key, content_type, max_bytes, expires_in=60)
    # The test talks to storage directly; browsers go through the web app's /s3 proxy.
    url = f"{get_settings().s3_endpoint.rstrip('/')}/{get_settings().s3_bucket}"
    return httpx.post(
        url, data=signed["fields"], files={"file": ("upload.md", data, content_type)}, timeout=10
    )


def test_ensure_bucket_is_idempotent() -> None:
    storage.ensure_bucket()
    storage.ensure_bucket()


def test_presigned_upload_then_inspect_download_delete() -> None:
    key = f"submissions/{uuid.uuid4()}/{uuid.uuid4()}/notes.md"

    response = _post(key, PAYLOAD)
    assert response.status_code in {200, 201, 204}, response.text

    stored = storage.inspect(key)
    assert stored.size_bytes == len(PAYLOAD)
    assert stored.sha256 == hashlib.sha256(PAYLOAD).hexdigest()  # unchanged after the round trip
    assert stored.content_type == CONTENT_TYPE

    assert b"".join(storage.stream(key)) == PAYLOAD

    storage.delete(key)
    with pytest.raises(storage.ObjectMissing):
        storage.inspect(key)


def test_presigned_upload_rejects_oversized_file() -> None:
    key = f"submissions/{uuid.uuid4()}/{uuid.uuid4()}/big.md"
    response = _post(key, b"x" * 2048, max_bytes=1024)
    assert response.status_code >= 400
    with pytest.raises(storage.ObjectMissing):
        storage.inspect(key)


def test_presigned_upload_rejects_empty_file() -> None:
    key = f"submissions/{uuid.uuid4()}/{uuid.uuid4()}/empty.md"
    response = _post(key, b"")
    assert response.status_code >= 400
    with pytest.raises(storage.ObjectMissing):
        storage.inspect(key)


def test_presigned_upload_rejects_other_content_type() -> None:
    key = f"submissions/{uuid.uuid4()}/{uuid.uuid4()}/notes.md"
    signed = storage.presign_upload(key, CONTENT_TYPE, 1024 * 1024, expires_in=60)
    fields = {**signed["fields"], "Content-Type": "text/html"}
    url = f"{get_settings().s3_endpoint.rstrip('/')}/{get_settings().s3_bucket}"
    response = httpx.post(
        url, data=fields, files={"file": ("x.md", PAYLOAD, "text/html")}, timeout=10
    )
    assert response.status_code >= 400


def test_presigned_upload_cannot_write_another_key() -> None:
    key = f"submissions/{uuid.uuid4()}/{uuid.uuid4()}/notes.md"
    other = f"submissions/{uuid.uuid4()}/{uuid.uuid4()}/other.md"
    signed = storage.presign_upload(key, CONTENT_TYPE, 1024 * 1024, expires_in=60)
    fields = {**signed["fields"], "key": other}
    url = f"{get_settings().s3_endpoint.rstrip('/')}/{get_settings().s3_bucket}"
    response = httpx.post(
        url, data=fields, files={"file": ("x.md", PAYLOAD, CONTENT_TYPE)}, timeout=10
    )
    assert response.status_code >= 400
    with pytest.raises(storage.ObjectMissing):
        storage.inspect(other)


def test_finalized_submission_keeps_original_bytes() -> None:
    instance = TaskInstance(id=uuid.uuid4())
    key = f"submissions/{instance.id}/{uuid.uuid4()}/notes.md"
    assert _post(key, PAYLOAD).status_code in {200, 201, 204}

    finalized_keys: list[str] = []
    artifacts = _validate(
        instance,
        {"notes": {"kind": "file", "accept": [".md"]}},
        [ArtifactIn(deliverable_id="notes", kind="file", upload_key=key)],
        get_settings(),
        finalized_keys,
    )
    artifact = artifacts[0]
    assert artifact.storage_key == finalized_keys[0]
    assert artifact.storage_key != key
    assert artifact.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert artifact.filename == "notes.md"

    replacement = b"Revised notes"
    assert _post(key, replacement).status_code in {200, 201, 204}
    assert b"".join(storage.stream(key)) == replacement
    assert b"".join(storage.stream(finalized_keys[0])) == PAYLOAD
