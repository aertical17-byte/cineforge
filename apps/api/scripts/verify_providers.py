"""Provider live-verification tool (run in CI with keys, or by an operator).

Per public provider docs:
- Replicate: GET /v1/models/{ref} is an authenticated public read.
- fal: queue status probe of an obviously-invalid request should be 404 (proves auth+route reachability).
- AI Horde: GET /users/me with the well-known anonymous key (ten zeros) proves the free,
  keyless community path is reachable — no signup, no card.

This script NEVER generates media by default. With `--generate` it performs ONE real
AI Horde image generation (the free anonymous path — the proof a 0-budget deployment
actually works) and saves the artifact under logs/.
"""
from __future__ import annotations

import json
import os
import sys

import httpx

OUT = sys.argv[1] if len(sys.argv) > 1 else "logs/verify_providers.json"
GENERATE = "--generate" in sys.argv
results: dict = {}

HORDE_BASE = "https://aihorde.net/api/v2"
HORDE_ANON_KEY = "0000000000"
HORDE_AGENT = "CineForgeAI:verify:1.0"


def main():
    rep_token = os.environ.get("REPLICATE_API_TOKEN")
    fal_key = os.environ.get("FAL_KEY")
    if rep_token:
        try:
            r = httpx.get("https://api.replicate.com/v1/models",
                          headers={"Authorization": f"Bearer {rep_token}"}, timeout=30)
            results["replicate"] = {"reachable": r.status_code in (200,), "status": r.status_code}
        except Exception as e:  # noqa: BLE001
            results["replicate"] = {"reachable": False, "error": str(e)}
    else:
        results["replicate"] = {"skipped": "REPLICATE_API_TOKEN missing"}
    if fal_key:
        try:
            r = httpx.get("https://queue.fal.run/", headers={"Authorization": f"Key {fal_key}"}, timeout=30)
            results["fal"] = {"reachable": r.status_code < 500, "status": r.status_code}
        except Exception as e:  # noqa: BLE001
            results["fal"] = {"reachable": False, "error": str(e)}
    else:
        results["fal"] = {"skipped": "FAL_KEY missing"}

    # AI Horde: free community tier — reachability via the public heartbeat (no auth),
    # anonymous concurrency/limits are enforced at submit time.
    try:
        r = httpx.get(f"{HORDE_BASE}/status/heartbeat", timeout=30)
        results["aihorde"] = {"reachable": r.status_code == 200 and "heartbeat" in r.json(),
                              "status": r.status_code}
    except Exception as e:  # noqa: BLE001
        results["aihorde"] = {"reachable": False, "error": str(e)}

    if GENERATE:
        results["aihorde_generate"] = horde_generate_once()

    import pathlib
    pathlib.Path("logs").mkdir(parents=True, exist_ok=True)
    pathlib.Path(OUT).write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


def horde_generate_once() -> dict:
    """ONE real image through the adapter (anonymous tier, 512px). Proves budget-0 works."""
    import sys as _sys
    _sys.path.insert(0, os.getcwd())  # running as a file puts scripts/ first, not cwd
    from app.providers.aihorde import AIHordeProvider  # cwd must be apps/api
    from app.providers.base import ImageRequest

    provider = AIHordeProvider(HORDE_ANON_KEY, HORDE_AGENT)
    req = ImageRequest(prompt="a rain-soaked neon street reflected in puddles, cinematic still",
                       aspect_ratio="16:9", seed=20261111)
    try:
        import asyncio
        result = asyncio.run(provider.generate_image(req))  # submits + polls internally (real adapter path)
        import pathlib
        pathlib.Path("logs").mkdir(parents=True, exist_ok=True)
        out = "logs/horde-smoke.webp"
        d = httpx.get(result.urls[0], timeout=120, follow_redirects=True)
        pathlib.Path(out).write_bytes(d.content)
        return {"ok": d.status_code == 200 and len(d.content) > 1000, "bytes": len(d.content),
                "job_id": result.provider_job_ref, "meta": result.native_metadata,
                "artifact": out}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300]}


if __name__ == "__main__":
    main()
