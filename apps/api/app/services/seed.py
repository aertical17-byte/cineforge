"""Registry seeding: plans, providers, models, presets, templates.

Model catalog defines SELECTED third-party engines via public provider docs at authoring
time. Entries marked `needs_verification` in notes are validated by scripts/verify_providers.py —
the deployment's honest status is exposed through /v1/providers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIModel, AIProvider, Plan, PresetRow, Template
from pathlib import Path as _P

DATA = _P(__file__).resolve().parents[3] / "packages" / "shared" / "data" / "creative_registries.json"

PLANS = [
    dict(code="free", name="Free", monthly_price_cents=0, yearly_price_cents=0, monthly_credits=100,
         max_concurrency=1, unlimited_models=[], features=["watermark-free downloads", "community templates"]),
    dict(code="creator", name="Creator", monthly_price_cents=2900, yearly_price_cents=29000, monthly_credits=1500,
         max_concurrency=2, unlimited_models=["flux-schnell"],
         features=["all standard engines", "camera presets", "elements library", "API access"]),
    dict(code="studio", name="Studio", monthly_price_cents=9900, yearly_price_cents=99000, monthly_credits=6000,
         max_concurrency=4, unlimited_models=["flux-schnell", "wan-14b"],
         features=["priority queue", "30s clips", "team projects", "compliance logging"]),
    dict(code="enterprise", name="Enterprise", monthly_price_cents=0, yearly_price_cents=0, monthly_credits=60000,
         max_concurrency=8, unlimited_models=[], features=["self-host option", "SSO", "dedicated capacity", "SLA"]),
]

PROVIDERS = [
    dict(id="replicate", name="Replicate", docs_url="https://replicate.com/docs", base_url="https://api.replicate.com/v1", requires_key="replicate_api_token"),
    dict(id="fal", name="fal.ai", docs_url="https://docs.fal.ai", base_url="https://queue.fal.run", requires_key="fal_key"),
    dict(id="mock", name="Mock (tests only)", docs_url="", base_url="", requires_key="AI_MOCK_MODE"),
]

MODELS = [
    # slug, provider, family, name, tasks, caps, costs, provider_model, provider_config
    dict(id="flux-schnell", provider_id="replicate", family="speed-image", display_name="FLUX Schnell (speed)",
         tasks=["image"], credits=(3, 0), provider_model="black-forest-labs/flux-schnell",
         caps=dict(supports_seed=True, supports_negative_prompt=False, supports_refs=False, max_batch=4,
                   aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"], resolutions=["standard"])),
    dict(id="flux-dev", provider_id="replicate", family="quality-image", display_name="FLUX Dev (quality)",
         tasks=["image"], credits=(12, 0), provider_model="black-forest-labs/flux-dev",
         caps=dict(supports_seed=True, supports_negative_prompt=False, supports_refs=False, max_batch=2,
                   aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"], resolutions=["standard", "4k"])),
    dict(id="stable-xl", provider_id="replicate", family="reference-image", display_name="SDXL (reference-friendly)",
         tasks=["image"], credits=(4, 0), provider_model="stability-ai/stable-diffusion-xl",
         caps=dict(supports_seed=True, supports_negative_prompt=True, supports_refs=True, max_batch=2,
                   aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"])),
    dict(id="flux-stdio", provider_id="fal", family="fast-reference", display_name="FLUX stdio (fal reference control)",
         tasks=["image"], credits=(4, 0), provider_model="fal-ai/flux/general/image-to-image",
         caps=dict(supports_seed=True, supports_refs=True, max_batch=2,
                   aspect_ratios=["1:1", "16:9", "9:16"], resolutions=["standard", "4k"])),
    dict(id="wan-14b", provider_id="replicate", family="keyframe-video", display_name="Wan 2.2 (first+last frame)",
         tasks=["video"], credits=(10, 4), provider_model="wan-video/wan-2.2-t2v-a14b",
         caps=dict(supports_seed=True, max_duration_s=8, supports_first_frame=True, supports_negative_prompt=True,
                   aspect_ratios=["16:9", "9:16", "1:1"])),
    dict(id="kling-standard", provider_id="fal", family="cinematic-video", display_name="Kling Standard (cinematic motion)",
         tasks=["video"], credits=(14, 8), provider_model="fal-ai/kling-video/v1/standard/text-to-video", min_plan="studio",
         caps=dict(supports_camera_control=True, max_duration_s=10, supports_negative_prompt=True,
                   aspect_ratios=["16:9", "9:16", "1:1"], structured_params=["camera"])),
    dict(id="kling-i2v", provider_id="fal", family="cinematic-video", display_name="Kling Image-to-Video",
         tasks=["video"], credits=(14, 8), provider_model="fal-ai/kling-video/v1/dev/image-to-video", min_plan="studio",
         caps=dict(supports_camera_control=True, max_duration_s=10, supports_first_frame=True,
                   aspect_ratios=["16:9", "9:16", "1:1"], structured_params=["camera"])),
    dict(id="mock-engine", provider_id="mock", family="test", display_name="Mock Engine (test env only)",
         tasks=["image", "video"], credits=(1, 1), provider_model="mock/engine",
         caps=dict(supports_seed=True, supports_negative_prompt=True, supports_refs=True,
                   supports_camera_control=True, max_duration_s=30, max_batch=4,
                   aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"])),
]

TEMPLATES = [
    dict(slug="launch-hero-orbit", name="Hero Orbit Trailer", category="cinematic", media_type="video",
         prompt="wide establishing shot of a glass atrium on a cloudy morning, silhouetted figures below",
         settings=dict(model_id="kling-standard", camera_move="orbit_right",
                       film_setup=dict(genre="epic", palette="steel_gray", lighting="natural", tempo="glacial"))),
    dict(slug="product-parallax", name="Product Parallax Reel", category="product", media_type="video",
         prompt="studio product on matte black pedestal, soft rim light, slow reveal",
         settings=dict(model_id="kling-standard", camera_move="orbit_left",
                       film_setup=dict(genre="general", palette="neutral_weave", lighting="studio", speed_ramp="flash_in"))),
    dict(slug="tokyo-street-fashion", name="Tokyo Street Fashion", category="image", media_type="image",
         prompt="full-height fashion look in a rainy neon alley, reflections on asphalt",
         settings=dict(model_id="stable-xl", aspect_ratio="3:4",
                       film_setup=dict(genre="general", palette="rose_neon", lighting="neon"))),
    dict(slug="vertigo-dream", name="Vertigo Dream", category="cinematic", media_type="video",
         prompt="hallway that keeps stretching, one figure always the same distance away",
         settings=dict(model_id="wan-14b", camera_move="dolly_zoom",
                       film_setup=dict(genre="drama", palette="cyan_dream", lighting="custom"))),
]

PRESET_GROUPS = ["camera_moves", "speed_ramps", "genres", "eras", "tempo", "camera_bodies", "lenses",
                 "apertures", "moveset_styles", "lighting_presets", "palettes", "image_style_presets"]


async def seed(session: AsyncSession, minimal: bool = False):
    for p in PLANS:
        if not (await session.execute(select(Plan).where(Plan.code == p["code"]))).scalar_one_or_none():
            session.add(Plan(**p))
    for pr in PROVIDERS:
        if not (await session.execute(select(AIProvider).where(AIProvider.id == pr["id"]))).scalar_one_or_none():
            session.add(AIProvider(**pr))
    for m in MODELS:
        if not (await session.execute(select(AIModel).where(AIModel.id == m["id"]))).scalar_one_or_none():
            base_cost, per_s = m["credits"]
            session.add(AIModel(id=m["id"], provider_id=m["provider_id"], family=m["family"],
                                display_name=m["display_name"], tasks=m["tasks"],
                                capabilities=m["caps"], credit_cost_base=base_cost,
                                credit_cost_per_second=per_s, provider_model=m["provider_model"],
                                min_plan=m.get("min_plan", "free"), description=m["display_name"]))
    data = json.loads(DATA.read_text())
    for group in PRESET_GROUPS:
        for row in data.get(group, []):
            rec_id = row["id"]
            exists = (await session.execute(
                select(PresetRow).where(PresetRow.id == rec_id, PresetRow.group == group))).scalar_one_or_none()
            if not exists:
                session.add(PresetRow(id=rec_id, group=group, name=row.get("name", rec_id), payload=row))
    if not minimal:
        for t in TEMPLATES:
            if not (await session.execute(select(Template).where(Template.slug == t["slug"]))).scalar_one_or_none():
                session.add(Template(**t))
    await session.commit()
