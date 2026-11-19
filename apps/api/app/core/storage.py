"""Object storage over the plain S3 API (ADR-011: no provider-specific SDKs or calls).

Uploads: the browser posts directly to storage with a presigned POST. A POST policy signs the
policy document, not the host, so the form can go through the web app's same-origin /s3 proxy.
The policy pins the object key, the content type and a size range (1 byte to the limit), so
empty and oversized files are rejected by storage itself.

Downloads are streamed through the API (see the submissions router), so permissions and RLS
are checked on every download and no long-lived download URLs exist.
"""

import hashlib
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

CHUNK = 1024 * 1024


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    content_type: str | None
    sha256: str


class ObjectMissing(Exception):
    pass


@lru_cache
def get_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket(client: BaseClient | None = None, bucket: str | None = None) -> None:
    """Create the bucket if it does not exist. Safe to call repeatedly."""
    client = client or get_client()
    bucket = bucket or get_settings().s3_bucket
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def presign_upload(key: str, content_type: str, max_bytes: int, expires_in: int) -> dict[str, Any]:
    """Presigned POST for exactly this key, content type and a 1..max_bytes size range."""
    settings = get_settings()
    post = get_client().generate_presigned_post(
        Bucket=settings.s3_bucket,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, max_bytes],
        ],
        ExpiresIn=expires_in,
    )
    # Browser-facing URL: the same-origin proxy path, followed by the bucket (path-style).
    return {
        "url": f"{settings.s3_public_upload_url.rstrip('/')}/{settings.s3_bucket}",
        "fields": post["fields"],
    }


def snapshot(source_key: str, destination_key: str) -> StoredObject:
    """Copy a staged upload to a server-owned key and inspect the finalized bytes."""
    settings = get_settings()
    try:
        get_client().copy_object(
            Bucket=settings.s3_bucket,
            Key=destination_key,
            CopySource={"Bucket": settings.s3_bucket, "Key": source_key},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
            raise ObjectMissing(source_key) from exc
        raise
    return inspect(destination_key)


def inspect(key: str) -> StoredObject:
    """Size, content type and SHA-256 come from the same object response."""
    settings = get_settings()
    try:
        obj = get_client().get_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        if exc.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
            raise ObjectMissing(key) from exc
        raise
    digest = hashlib.sha256()
    with closing(obj["Body"]) as body:
        for chunk in iter(lambda: body.read(CHUNK), b""):
            digest.update(chunk)
    return StoredObject(
        key=key,
        size_bytes=int(obj["ContentLength"]),
        content_type=obj.get("ContentType"),
        sha256=digest.hexdigest(),
    )


def stream(key: str) -> Iterator[bytes]:
    settings = get_settings()
    try:
        body = get_client().get_object(Bucket=settings.s3_bucket, Key=key)["Body"]
    except ClientError as exc:
        raise ObjectMissing(key) from exc
    yield from iter(lambda: body.read(CHUNK), b"")


def delete(key: str) -> None:
    get_client().delete_object(Bucket=get_settings().s3_bucket, Key=key)
