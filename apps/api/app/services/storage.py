"""Storage: S3-compatible backend (boto3) or local + HMAC-signed URLs (dev/CI)."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import uuid
from pathlib import Path
from typing import Tuple

from app.core.config import get_settings
from app.core.security import sign_url_token


class StorageService:
    def __init__(self):
        s = get_settings()
        self.backend = s.storage_backend
        self.local_dir = Path(s.storage_local_dir)
        if self.backend == "local":
            self.local_dir.mkdir(parents=True, exist_ok=True)

    async def put(self, data: bytes, mime: str, user_id: str = "anon",
                  filename: str | None = None) -> Tuple[str, str]:
        """Returns (storage_key, public_or_signed_url)."""
        ext = _EXT.get(mime.split(";")[0].strip(), "bin")
        key = f"{user_id}/{dt.datetime.now(dt.timezone.utc):%Y%m}/{uuid.uuid4().hex}.{filename or ext}"
        if self.backend == "s3":
            import boto3  # deferred import; not installed in test image if unused? (it is, but keep clean)

            s = get_settings()
            s3 = boto3.client(
                "s3", region_name=s.s3_region, endpoint_url=s.s3_endpoint_url,
                aws_access_key_id=s.aws_access_key_id, aws_secret_access_key=s.aws_secret_access_key,
            )
            s3.put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=mime)
            url = f"{s.s3_endpoint_url or f'https://{s.s3_bucket}.s3.{s.s3_region}.amazonaws.com'}/{key}"
            return key, url
        path = self.local_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key, f"/files/{key}?token={sign_url_token(key)}"

    async def public_or_signed_url(self, url: str, storage_key: str) -> str:
        if url:
            return url
        local = f"/files/{storage_key}?token={sign_url_token(storage_key)}"
        return local


_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg",
    "image/gif": "gif", "video/mp4": "mp4", "video/webm": "webm", "audio/mpeg": "mp3",
    "audio/wav": "wav", "application/json": "json", "text/html": "html",
}


def validate_upload(data: bytes, mime: str, max_bytes: int = 32 * 1024 * 1024) -> str | None:
    """Content-safety gate for uploads: returns allowed canonical mime or None."""
    if len(data) == 0 or len(data) > max_bytes:
        return None
    allowed = {"image/png", "image/jpeg", "image/webp"}
    sniffed = _sniff(data)
    if sniffed and sniffed in allowed:
        return sniffed
    return None


def _sniff(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
