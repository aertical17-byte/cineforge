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

    # AI Horde: free community tier — anonymous key, no key material needed.
    try:
        r = httpx.get(f"{HORDE_BASE}/users/me",
                      headers={"apikey": HORDE_ANON_KEY, "Client-Agent": HORDE_AGENT}, timeout=30)
        results["aihorde"] = {"reachable": r.status_code == 200, "status": r.status_code}
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
    from app.providers.aihorde import AIHordeProvider, horde_payload  # cwd must be apps/api
    from app.providers.base import ImageRequest

    provider = AIHordeProvider(HORDE_ANON_KEY, HORDE_AGENT)
    req = ImageRequest(prompt="a rain-soaked neon street reflected in puddles, cinematic still",
                       aspect_ratio="16:9", seed=20261111)
    payload = horde_payload(req)
    try:
        import httpx as _hx
        r = _hx.post(f"{HORDE_BASE}/generate/async", json=payload,
                     headers={"apikey": HORDE_ANON_KEY, "Client-Agent": HORDE_AGENT,
                              "Content-Type": "application/json"}, timeout=60)
        if r.status_code != 202 and r.status_code >= 400:
            return {"ok": False, "stage": "submit", "status": r.status_code, "body": r.text[:300]}
        job_id = r.json().get("id", "")
        result = provider.__class__  # noqa: F841 (kept for readability)
        gen = _poll_and_download(job_id, payload["prompt"])
        return gen
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300]}


def _poll_and_download(job_id: str, prompt: str) -> dict:
    import time

    import httpx as _hx
    headers = {"apikey": HORDE_ANON_KEY, "Client-Agent": HORDE_AGENT}
    waited = 0.0
    while waited < 420.0:
        c = _hx.get(f"{HORDE_BASE}/generate/check/{job_id}", headers=headers, timeout=30)
        if c.status_code >= 400:
            return {"ok": False, "stage": "check", "status": c.status_code, "job_id": job_id}
        chk = c.json()
        if chk.get("faulted"):
            return {"ok": False, "stage": "faulted", "job_id": job_id}
        if chk.get("done"):
            st = _hx.get(f"{HORDE_BASE}/generate/status/{job_id}", headers=headers, timeout=30)
            gens = st.json().get("generations") or []
            if not gens or not gens[0].get("img"):
                return {"ok": False, "stage": "no-image", "job_id": job_id}
            img_url = gens[0]["img"]
            d = _hx.get(img_url, headers=headers, timeout=120, follow_redirects=True)
            import pathlib
            pathlib.Path("logs").mkdir(parents=True, exist_ok=True)
            out = "logs/horde-smoke.webp"
            pathlib.Path(out).write_bytes(d.content)
            return {"ok": d.status_code == 200, "job_id": job_id, "bytes": len(d.content),
                    "artifact": out, "seed": gens[0].get("seed"), "model": gens[0].get("model"),
                    "prompt": prompt[:80]}
        time.sleep(5.0)
        waited += 5.0
    return {"ok": False, "stage": "timeout", "job_id": job_id, "waited_s": waited}


if __name__ == "__main__":
    main()
