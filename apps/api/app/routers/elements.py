"""Characters/elements: profile creation, photo attestation, reusable identities."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Element, ElementPhoto, Asset, User
from app.schemas import ElementCreate, ElementOut, ElementTrainingRequest
from app.services.auth import current_user
from app.core.db import session

router = APIRouter(prefix="/v1/elements", tags=["elements"])


class ElementUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    attributes: dict | None = None


@router.get("", response_model=list[ElementOut])
async def list_elements(type: str | None = None, user: User = Depends(current_user),
                        s: AsyncSession = Depends(session)):
    q = select(Element).where(Element.user_id == user.id, Element.deleted_at.is_(None))
    if type:
        q = q.where(Element.type == type)
    rows = (await s.execute(q.order_by(Element.created_at.desc()))).scalars().all()
    return rows


@router.post("", response_model=ElementOut, status_code=201)
async def create_element(body: ElementCreate, user: User = Depends(current_user),
                         s: AsyncSession = Depends(session)):
    if body.type == "character" and not user.consent_likeness:
        raise HTTPException(403, "likeness consent missing — confirm you may use the depicted person's face")
    e = Element(user_id=user.id, type=body.type, name=body.name, description=body.description,
                attributes=body.attributes)
    s.add(e)
    await s.commit()
    await s.refresh(e)
    return e


@router.post("/{element_id}/photos", status_code=202)
async def attach_training_photos(element_id: str, body: ElementTrainingRequest,
                                 user: User = Depends(current_user), s: AsyncSession = Depends(session)):
    e = (await s.execute(select(Element).where(Element.id == element_id,
                                               Element.user_id == user.id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "element not found")
    valid = 0
    for aid in body.photo_asset_ids:
        a = await s.get(Asset, aid)
        if a and a.user_id == user.id:
            s.add(ElementPhoto(element_id=e.id, asset_id=aid, checked=True))
            valid += 1
    if valid < 20:
        raise HTTPException(422, f"identity training requires ≥20 verified uploads of one person (received {valid})")
    e.training_status = "training"
    await s.commit()
    return {"status": "queued", "note": "identity training requires a trained-identity engine; "
                                        "status stays 'training' until configured"}


@router.post("/{element_id}/viewport")  # lightweight keep-alive endpoint for the editor
async def element_keepalive(element_id: str, user: User = Depends(current_user),
                            s: AsyncSession = Depends(session)):
    e = await s.get(Element, element_id)
    if not e or e.user_id != user.id:
        raise HTTPException(404, "element not found")
    return {"id": e.id, "training_status": e.training_status}
