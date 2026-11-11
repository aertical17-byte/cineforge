"""Flowboard pipeline tests: chains run honestly — mock engines only, refunds on failure."""
from __future__ import annotations

import pytest

from tests.conftest import _token, auth_header


def _chain_body() -> dict:
    return {
        "name": "Rain short",
        "steps": [
            {"kind": "image", "model_id": "mock-engine", "prompt": "hero frame", "aspect_ratio": "16:9"},
            {"kind": "video", "model_id": "mock-engine", "prompt": "bring the frame alive", "duration_s": 4},
        ],
    }


@pytest.mark.asyncio
async def test_chain_spawns_next_step_and_succeeds(client):
    app, http = client
    tok = await _token(http, "pipe.a@example.com")
    h = auth_header(tok)

    r = await http.post("/v1/pipelines", headers=h, json=_chain_body())
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["status"] == "running"

    d = (await http.get(f"/v1/pipelines/{pid}", headers=h)).json()
    assert len(d["steps"]) == 2
    assert d["steps"][0]["generation_id"], "step 0 spawns immediately"
    assert d["steps"][1]["status"] == "pending", "later steps wait for the chain to advance"
    assert d["steps"][1]["generation_id"] is None

    from app.services.jobs import process_pending

    async def drained(rounds: int = 12):
        """process_pending shares one SQLite DB with every test file; earlier tests
        (e.g. the 402-insolvency test) intentionally leave queued jobs behind, so
        drain rounds until THIS pipeline's step actually settles."""
        for _ in range(rounds):
            d = (await http.get(f"/v1/pipelines/{pid}", headers=h)).json()
            if d["steps"][0]["status"] in ("succeeded", "failed"):
                return d
            await process_pending(batch=4)
        return (await http.get(f"/v1/pipelines/{pid}", headers=h)).json()

    d = await drained()  # image step
    assert d["steps"][0]["status"] == "succeeded"
    assert d["steps"][0]["assets"], "image step produced an asset"
    assert d["steps"][1]["generation_id"] is not None, "worker spawned the video step"
    assert d["steps"][1]["task"] == "img2video", "video step is fed by the previous asset"

    for _ in range(12):  # video step
        d = (await http.get(f"/v1/pipelines/{pid}", headers=h)).json()
        if d["status"] in ("succeeded", "failed", "canceled"):
            break
        await process_pending(batch=4)
    assert d["status"] == "succeeded", d
    assert all(st["status"] == "succeeded" for st in d["steps"])
    assert all(st["assets"] for st in d["steps"])

    # the video generation truly consumed the image asset as its first frame
    gen2 = (await http.get(f"/v1/generations/{d['steps'][1]['generation_id']}", headers=h)).json()
    assert gen2["params"]["first_frame_asset_id"] == d["steps"][0]["assets"][0]["id"]

    # ledger: two spends, one per step (mock-engine image 1cr; video = 1 base + 4s·1cr/s)
    ledger = (await http.get("/v1/credits/summary", headers=h)).json()
    assert ledger["balance"] == 200 - 6


@pytest.mark.asyncio
async def test_chain_validation_rejects_bad_specs(client):
    app, http = client
    tok = await _token(http, "pipe.b@example.com")
    h = auth_header(tok)

    r = await http.post("/v1/pipelines", headers=h, json={"steps": []})
    assert r.status_code == 422, "a chain without steps is a spec error"

    bad = _chain_body()
    bad["steps"][0]["model_id"] = "does-not-exist"
    r = await http.post("/v1/pipelines", headers=h, json=bad)
    assert r.status_code == 404, r.text

    unknown_kind = _chain_body()
    unknown_kind["steps"][1]["kind"] = "podcast"
    r = await http.post("/v1/pipelines", headers=h, json=unknown_kind)
    assert r.status_code == 422, r.text
