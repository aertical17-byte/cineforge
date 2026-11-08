"""Filesystem locations that must work in a monorepo checkout, CI job, and Docker image alike."""
from __future__ import annotations

from pathlib import Path

REGISTRY_RELATIVE = Path("packages") / "shared" / "data" / "creative_registries.json"


def shared_registry_path() -> Path:
    """Locate packages/shared/data/creative_registries.json without assuming a fixed depth.

    The API code lives at apps/api/app/services in a checkout but is flattened to
    /app/app inside the Docker image, so a fixed parents[N] cannot serve both.
    Walk upward (cwd first) and take the first ancestor that actually contains the file.
    """
    bases = [Path.cwd(), *Path(__file__).resolve().parents]
    for base in bases:
        candidate = base / REGISTRY_RELATIVE
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"{REGISTRY_RELATIVE} not found under cwd or any ancestor of {Path(__file__).resolve()}"
    )
