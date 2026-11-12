"""Auth flow tests."""
from __future__ import annotations

import pytest

from tests.conftest import _token, auth_header


@pytest.mark.asyncio
async def test_register_login_me(client):
    app, http = client

    tok = await _token(http, "auth.a@example.com")
    me = await http.get("/v1/auth/me", headers=auth_header(tok))
    assert me.status_code == 200
    assert me.json()["email"] == "auth.a@example.com"

    bad = await http.post("/v1/auth/login", json={"email": "auth.a@example.com", "password": "WrongPassw0rd"})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_password_policy(client):
    app, http = client
    r = await http.post("/v1/auth/register", json={"email": "auth.b@example.com", "password": "weak12345"})
    assert r.status_code == 422
    r = await http.post("/v1/auth/register", json={"email": "auth.b@example.com", "password": "NoDigitsHere"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_allowlist(client):
    app, http = client
    tok = await _token(http, "admin.seeded@example.com")
    me = (await http.get("/v1/auth/me", headers=auth_header(tok))).json()
    assert me["is_admin"] is False  # not in allowlist


@pytest.mark.asyncio
async def test_welcome_credits_granted(client):
    app, http = client
    tok = await _token(http, "auth.c@example.com")
    s = (await http.get("/v1/credits/summary", headers=auth_header(tok))).json()
    from app.core.config import get_settings
    assert s["balance"] == get_settings().free_signup_credits  # "no limits" mode value


@pytest.mark.asyncio
async def test_guest_no_login(client):
    """No-login mode: /auth/guest mints an account with welcome credits, no credentials."""
    app, http = client
    r = await http.post("/v1/auth/guest")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"].startswith("guest-")
    me = await http.get("/v1/auth/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200
    s = (await http.get("/v1/credits/summary", headers=auth_header(body["access_token"]))).json()
    from app.core.config import get_settings
    assert s["balance"] == get_settings().free_signup_credits


@pytest.mark.asyncio
async def test_guest_credits_never_expire(client):
    """free_signup_credits_days=0 must mean "no expiry": the guest's only lot has no expiry date."""
    app, http = client
    r = await http.post("/v1/auth/guest")
    tok = r.json()["access_token"]
    s = (await http.get("/v1/credits/summary", headers=auth_header(tok))).json()
    assert s["balance"] > 0
    assert s["soonest_expiry_date"] is None
