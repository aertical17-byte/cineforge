"""Provider capability registry + credit pricing (source of truth = ai_models rows)."""
from __future__ import annotations

from typing import Any, Dict, Optional

CAP_DEFAULTS: Dict[str, Any] = {
    "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"],
    "resolutions": ["standard"],
    "max_duration_s": 0,
    "supports_seed": False,
    "supports_negative_prompt": False,
    "supports_refs": False,
    "supports_camera_control": False,     # structured provider controls (beyond prompt rendering)
    "supports_last_frame": False,
    "supports_audio_native": False,
    "supports_upscale": False,
    "max_batch": 1,
}

# Generic cinematography term → it is always safe to RENDER these in text prompts for any
# text-driven model. Structured provider params are only sent when capabilities permit.
PROMPT_ALWAYS_SAFE_GROUPS = {"camera_moves", "speed_ramps", "tempo", "lenses", "camera_bodies",
                             "palettes", "lighting_presets", "moveset_styles", "genres", "eras"}


def caps(model_like: Any) -> Dict[str, Any]:
    out = dict(CAP_DEFAULTS)
    raw = getattr(model_like, "capabilities", None)
    if isinstance(raw, dict):
        out.update({k: v for k, v in raw.items() if v is not None})
    return out


def credit_cost(model_like: Any, media_type: str, duration_s: int = 0, batch: int = 1,
                resolution: Optional[str] = None) -> int:
    """Deterministic, displayed-to-the-user pricing. Resolution premium: 2× for 4k tiers."""
    base = int(getattr(model_like, "credit_cost_base", 0) or 0)
    per_s = int(getattr(model_like, "credit_cost_per_second", 0) or 0)
    cost = base if media_type == "image" else base + per_s * max(duration_s, 1)
    if (resolution or "").lower().startswith(("4k", "uhd", "1920", "2160")):
        cost *= 2
    return max(1, cost) * max(1, batch)
