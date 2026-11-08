"""Prompt engine: turns user prompt + creative registries into provider-ready payloads.

Hard rules:
- Only compose parameters a model's capability registry says it supports; unsupported choices are
  rendered as *text* (always safe) or rejected with `UNSUPPORTED_PARAMETER` (structured controls).
- Nothing here invents functionality the provider doesn't have; the UI shows capability badges from
  /models, and the API is the second line of defense.
Original authoring; fragments live in packages/shared/data/creative_registries.json.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from app.core.paths import shared_registry_path
from app.providers.base import ImageRequest, VideoRequest
from app.services.registry import caps, credit_cost  # re-export convenience

_REGISTRY_JSON = shared_registry_path()


@lru_cache(maxsize=1)
def registries() -> Dict[str, Any]:
    return json.loads(_REGISTRY_JSON.read_text())


def _index(group: str) -> Dict[str, Dict[str, Any]]:
    return {row["id"]: row for row in registries().get(group, [])}


def compose_prompt(base_prompt: str, film: Optional[Dict[str, Any]], camera_move: Optional[str],
                   emotion_strength: Optional[float]) -> str:
    parts: List[str] = [base_prompt.strip()]
    if film:
        idx = {
            "genre": _index("genres"),
            "era": _index("eras"),
            "tempo": _index("tempo"),
            "camera_body": _index("camera_bodies"),
            "lens": _index("lenses"),
            "palette": _index("palettes"),
            "lighting": _index("lighting_presets"),
            "speed_ramp": _index("speed_ramps"),
            "moveset_style": _index("moveset_styles"),
        }
        for key, table in idx.items():
            row = table.get(film.get(key))
            fragment = (row or {}).get("fragment") or (row or {}).get("grade_fragment")
            if fragment:
                parts.append(fragment)
        cl = film.get("custom_lighting") or {}
        if film.get("lighting") == "custom" and cl:
            bits = []
            if cl.get("color"):
                bits.append(f"{cl['color']} light color")
            if cl.get("brightness"):
                bits.append(f"{cl['brightness']} brightness")
            if cl.get("diffusion"):
                bits.append(f"{cl['diffusion']} diffusion")
            if cl.get("angle"):
                bits.append(f"light at {cl['angle']} angle")
            if bits:
                parts.append("custom lighting setup: " + ", ".join(bits))
    if camera_move:
        row = _index("camera_moves").get(camera_move)
        if row and row.get("fragment"):
            parts.append(row["fragment"])
    if emotion_strength not in (None, 0):
        level = "subtle" if emotion_strength < 0.34 else ("clearly visible" if emotion_strength < 0.67 else "overwhelming")
        parts.append(f"character emotions played {level} on screen")
    return ", ".join(parts)


def resolve_camera(model_caps: Dict[str, Any], camera_move: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Returns (prompt_fragment, structured_camera_control or None).

    Structured control dict is passed to provider only when the model declares support.
    """
    if not camera_move:
        return "", None
    row = _index("camera_moves").get(camera_move)
    if not row:
        return "", None
    structured = row.get("camera_control_mapping") or None
    if structured and not model_caps.get("supports_camera_control"):
        structured = None  # degrade to prompt text; never send invented provider params
    return row["fragment"], structured


def build_image_request(model_row: Any, prompt: str, negative_prompt: str, aspect: str,
                        resolution: Optional[str], seed: Optional[int], steps: Optional[int],
                        guidance: Optional[float], batch: int, reference_urls: List[str],
                        reference_strength: Optional[float], provider_model: str,
                        provider_config: Dict[str, Any]) -> ImageRequest:
    c = caps(model_row)
    if batch > int(c.get("max_batch", 1) or 1):
        batch = 1
    req = ImageRequest(
        prompt=prompt, negative_prompt=negative_prompt if c.get("supports_negative_prompt") else "",
        aspect_ratio=aspect if aspect in (c.get("aspect_ratios") or ["1:1"]) else "1:1",
        resolution=resolution, seed=seed if c.get("supports_seed") else None,
        steps=steps, guidance=guidance, batch=batch, reference_urls=reference_urls,
        reference_strength=reference_strength, provider_model=provider_model,
        provider_config=provider_config or {},
    )
    if reference_urls and not c.get("supports_refs"):
        req.reference_urls = []  # capability enforcement with honest degradation
    return req


def build_video_request(model_row: Any, prompt: str, negative_prompt: str, aspect: str,
                        duration_s: int, seed: Optional[int], first_frame_url: Optional[str],
                        reference_urls: List[str], camera_control: Optional[Dict[str, Any]],
                        provider_model: str, provider_config: Dict[str, Any]) -> VideoRequest:
    c = caps(model_row)
    max_dur = int(c.get("max_duration_s") or 0)
    duration = min(max(int(duration_s or 5), 1), max_dur or 5)
    if first_frame_url and not c.get("supports_first_frame", True):
        first_frame_url = None
    if reference_urls and not c.get("supports_refs"):
        reference_urls = []
    return VideoRequest(
        prompt=prompt, negative_prompt=negative_prompt if c.get("supports_negative_prompt") else "",
        aspect_ratio=aspect if aspect in (c.get("aspect_ratios") or ["16:9"]) else "16:9",
        duration_s=duration, seed=seed if c.get("supports_seed") else None,
        first_frame_url=first_frame_url, reference_urls=reference_urls,
        camera_control=camera_control if (camera_control and c.get("supports_camera_control")) else None,
        provider_model=provider_model, provider_config=provider_config or {},
    )
