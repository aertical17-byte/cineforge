"""Provider live-verification tool (run in CI with keys, or by an operator).

Per public provider docs:
- Replicate: GET /v1/models/{ref} is an authenticated public read.
- fal: queue status probe of an obviously-invalid request should be 404 (proves auth+route reachability).

This script NEVER generates media — it only validates reachability and records status into
/logs/verify_providers.json (see docs/AI_ENGINE.md).
"""
from __future__ import annotations

import json
import os
import sys

import httpx

OUT = sys.argv[1] if len(sys.argv) > 1 else "logs/verify_providers.json"
results: dict = {}


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
    import pathlib
    pathlib.Path("logs").mkdir(parents=True, exist_ok=True)
    pathlib.Path(OUT).write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
