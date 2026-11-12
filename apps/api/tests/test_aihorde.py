"""AI Horde provider: payload builder units + honest-disable behavior (hermetic — no network)."""
from __future__ import annotations

import pytest

from tests.conftest import _token, auth_header


def test_horde_payload_builder_pure():
    from app.providers.aihorde import horde_payload, horde_size
    from app.providers.base import ImageRequest

    assert horde_size("16:9") == (448, 256)  # multiple of 64: the horde validates this live
    assert horde_size("nonsense") == (512, 512)  # safe default

    req = ImageRequest(prompt="a rainy neon alley", negative_prompt="blurry",
                       aspect_ratio="3:4", seed=99, steps=80, guidance=7.0)
    payload = horde_payload(req)
    assert payload["params"]["width"] == 384 and payload["params"]["height"] == 512
    assert payload["params"]["steps"] == 50, "anonymous tier steps are capped at 50"
    assert payload["params"]["seed"] == "99", "horde schema wants seed as a string"
    assert payload["params"]["cfg_scale"] == 7.0
    assert payload["prompt"] == "a rainy neon alley ### blurry", "negative rides the documented separator"
    assert payload["nsfw"] is False

    plain = horde_payload(ImageRequest(prompt="just a prompt"))
    assert plain["prompt"] == "just a prompt"
    assert "seed" not in plain["params"], "seed omitted when not requested"


@pytest.mark.asyncio
async def test_horde_disabled_in_test_env_fails_honestly_and_refunds(client):
    """The free community engine is real, but tests must stay hermetic: generating with it
    in the test environment ends provider_not_configured + automatic refund — never a fake."""
    app, http = client
    tok = await _token(http, "horde.a@example.com")
    h = auth_header(tok)

    r = await http.post("/v1/generations", headers=h, json={
        "media_type": "image", "task": "text2img", "model_id": "horde-sdxl",
        "prompt": "community-powered frame", "aspect_ratio": "16:9",
    })
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    assert r.json()["estimated_credits"] == 2  # horde costs 2cr: real work, ~zero euros

    from app.services.jobs import process_pending
    await process_pending(batch=3)

    d = (await http.get(f"/v1/generations/{gid}", headers=h)).json()
    assert d["status"] == "failed", d
    assert d["error_code"] == "provider_not_configured", d
    assert len(d["assets"]) == 0

    ledger = (await http.get("/v1/credits/summary", headers=h)).json()
    assert ledger["balance"] == 200, "2 reserved credits refunded on honest failure"
