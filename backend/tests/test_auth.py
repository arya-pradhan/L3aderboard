"""End-to-end auth flow: register -> login -> /auth/me, plus failure cases."""
from __future__ import annotations

from httpx import AsyncClient

REGISTER = {
    "username": "ashley",
    "email": "ashley@example.com",
    "password": "supersecret123",
}


async def test_register_returns_user(client: AsyncClient) -> None:
    resp = await client.post("/auth/register", json=REGISTER)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == "ashley"
    assert body["email"] == "ashley@example.com"
    assert body["steam_id"] is None
    assert "id" in body
    # Password material must never be serialized back.
    assert "password" not in body
    assert "hashed_password" not in body


async def test_duplicate_registration_conflicts(client: AsyncClient) -> None:
    await client.post("/auth/register", json=REGISTER)
    resp = await client.post("/auth/register", json=REGISTER)
    assert resp.status_code == 409


async def test_login_and_me(client: AsyncClient) -> None:
    await client.post("/auth/register", json=REGISTER)

    # OAuth2 password flow uses form-encoded data.
    login = await client.post(
        "/auth/login",
        data={"username": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert token

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == REGISTER["email"]


async def test_login_by_username(client: AsyncClient) -> None:
    await client.post("/auth/register", json=REGISTER)
    login = await client.post(
        "/auth/login",
        data={"username": REGISTER["username"], "password": REGISTER["password"]},
    )
    assert login.status_code == 200, login.text


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post("/auth/register", json=REGISTER)
    login = await client.post(
        "/auth/login",
        data={"username": REGISTER["email"], "password": "wrongpassword"},
    )
    assert login.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
