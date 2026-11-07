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
    assert s["balance"] == 200
