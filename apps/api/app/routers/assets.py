"""Assets: upload (validated), listing, like/unlike, delete, signed local file serving."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path as FsPath

from fastapi import (APIRouter, Depends, File, HTTPException, Query, Request, UploadFile,
                     status)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import session
from app.core.security import sign_url_token
from app.models import Asset, Upload, User
from app.schemas import AssetList, AssetOut
from app.services.auth import current_user
from app.services.storage import storage, validate_upload

router = APIRouter(prefix="/v1/assets", tags=["assets"])
router_files = APIRouter(tags=["files"])

MAX_UPLOAD = 32 * 1024 * 1024


@router.post("/upload", response_model=AssetOut, status_code=201)
async def upload_asset(file: UploadFile = File(...), purpose: str = Query(default="reference"),
                       project_id: str | None = Query(default=None),
                       user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    data = await file.read()
    ok_mime = validate_upload(data, file.content_type or "", MAX_UPLOAD)
    if not ok_mime:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            "unsupported or unsafe upload (png/jpeg/webp ≤ 32MB)")
    key, url = await storage.put(data, ok_mime, user.id)
    a = Asset(user_id=user.id, project_id=project_id, source="upload", kind="image",
              storage_key=key, url=url, mime=ok_mime, size_bytes=len(data))
    s.add(a)
    s.add(Upload(user_id=user.id, asset_id=None, purpose=purpose,
                 original_name=file.filename or "", mime=ok_mime, size_bytes=len(data)))
    await s.commit()
    await s.refresh(a)
    return a


@router.get("", response_model=AssetList)
async def list_assets(kind: str | None = None, source: str | None = None,
                      project_id: str | None = None, liked: bool | None = None,
                      search: str | None = None, cursor: int | None = None, limit: int = Query(50, le=100),
                      user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    q = select(Asset).where(Asset.user_id == user.id, Asset.deleted_at.is_(None), Asset.source != "internal")
    if kind in ("image", "video", "audio"):
        q = q.where(Asset.kind == kind)
    if source in ("upload", "generation"):
        q = q.where(Asset.source == source)
    if project_id:
        q = q.where(Asset.project_id == project_id)
    if liked is not None:
        q = q.where(Asset.is_liked.is_(liked))
    if search:
        q = q.where(Asset.storage_key.contains(search))
    if cursor is not None:
        q = q.where(Asset.id < cursor)
    q = q.order_by(Asset.created_at.desc()).limit(limit)
    rows = (await s.execute(q)).scalars().all()
    return AssetList(items=[AssetOut.model_validate(a) for a in rows],
                     next=rows[-1].id if len(rows) == limit else None)


@router.post("/{asset_id}/like", response_model=AssetOut)
async def like(asset_id: str, user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    a = (await s.execute(select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "asset not found")
    a.is_liked = not a.is_liked
    await s.commit()
    await s.refresh(a)
    return a


@router.delete("/{asset_id}", status_code=204)
async def delete(asset_id: str, user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    a = (await s.execute(select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "asset not found")
    a.deleted_at = dt.datetime.now(dt.timezone.utc)
    await s.commit()
    return None


@router_files.get("/files/{path:path}")
async def serve_local_file(path: str, token: str, request: Request):
    """HMAC-signed local file serving (mirrors S3 presigned URL semantics; only up to expiry)."""
    s = get_settings()
    if s.storage_backend != "local":
        raise HTTPException(404, "not available in this storage mode")
    if not _valid(path, token):
        raise HTTPException(404, "unsigned or expired url")
    root = FsPath(s.storage_local_dir).resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)) or not target.exists():
        raise HTTPException(404, "not found")
    return FileResponse(target, headers={"Cache-Control": "private, max-age=3600"})


def _valid(path: str, token: str) -> bool:
    from app.core.security import sign_url_token as s_
    import hmac
    import hashlib

    _settings = get_settings()
    exp, sig = token.split(".", 1)
    try:
        if int(float(exp)) < int(dt.datetime.now(dt.timezone.utc).timestamp()):
            return False
    except ValueError:
        return False
    good = hmac.new(_settings.jwt_secret.encode(), f"{path}:{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, sig)
