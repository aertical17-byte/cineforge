"""API endpoint behavior tests (projects, assets, registries, elements gating)."""
from __future__ import annotations

import pytest

from tests.conftest import _token, auth_header


@pytest.mark.asyncio
async def test_project_crud(client):
    app, http = client
    tok = await _token(http, "proj.a@example.com")
    h = auth_header(tok)

    created = (await http.post("/v1/projects", headers=h, json={"name": "Campaign Q4"})).json()
    pid = created["id"]
    updated = (await http.patch(f"/v1/projects/{pid}", headers=h, json={"name": "Campaign Q5"})).json()
    assert updated["name"] == "Campaign Q5"
    assert (await http.delete(f"/v1/projects/{pid}", headers=h)).status_code == 204
    assert (await http.get(f"/v1/projects/{pid}", headers=h)).status_code == 404


@pytest.mark.asyncio
async def test_upload_validation(client):
    app, http = client
    tok = await _token(http, "proj.b@example.com")
    h = auth_header(tok)

    r = await http.post("/v1/assets/upload", headers=h, files={"file": ("x.exe", b"MZbad", "application/x-exe")})
    assert r.status_code == 415

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    r = await http.post("/v1/assets/upload", headers=h, files={"file": ("x.png", png, "image/png")})
    assert r.status_code == 201
    assert r.json()["kind"] == "image"


@pytest.mark.asyncio
async def test_model_capability_enforcement(client):
    app, http = client
    tok = await _token(http, "caps.a@example.com")
    h = auth_header(tok)

    bad_ar = await http.post("/v1/generations", headers=h, json={
        "media_type": "image", "task": "text2img", "model_id": "stable-xl",
        "prompt": "x", "aspect_ratio": "21:9",
    })
    assert bad_ar.status_code == 422

    plan_gate = await http.post("/v1/generations", headers=h, json={
        "media_type": "video", "task": "text2video", "model_id": "kling-standard",
        "prompt": "gated", "duration_s": 5,
    })
    assert plan_gate.status_code == 402  # studio-plan engine on free plan


@pytest.mark.asyncio
async def test_elements_likeness_consent(client):
    app, http = client
    tok = await _token(http, "elem.a@example.com")
    h = auth_header(tok)
    r = await http.post("/v1/elements", headers=h, json={"type": "character", "name": "Nova"})
    assert r.status_code == 403  # no likeness consent


@pytest.mark.asyncio
async def test_registered_camera_registry_exposed(client):
    app, http = client
    tok = await _token(http, "reg.a@example.com")
    cam = (await http.get("/v1/registry/camera_moves", headers=auth_header(tok))).json()
    ids = {c["id"] for c in cam}
    assert {"dolly_zoom", "orbit_left", "crane_up", "fpv"} <= ids
