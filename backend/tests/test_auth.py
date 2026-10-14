from app.security import hash_password, verify_password
from tests.conftest import PASSWORD


def test_password_hash_roundtrip():
    h = hash_password("s3cret-passphrase")
    assert h != "s3cret-passphrase" and h.startswith("$argon2")
    assert verify_password("s3cret-passphrase", h)
    assert not verify_password("wrong", h)


async def login(client, email="candidate@example.com", password=PASSWORD):
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def test_login_sets_httponly_cookie_and_me_works(client, user):
    r = await login(client, email="CANDIDATE@example.com")  # email is case-insensitive
    assert r.status_code == 200
    cookie = r.headers["set-cookie"]
    assert "session=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"id": user.id, "email": "candidate@example.com", "display_name": "Candidate", "target_band": 7.0}


async def test_wrong_password_and_unknown_email_get_same_401(client, user):
    a = await login(client, password="nope")
    b = await login(client, email="nobody@example.com")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


async def test_protected_route_needs_cookie(client):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_tampered_token_rejected(client, user):
    client.cookies.set("session", "not.a.jwt")
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_logout_clears_cookie(client, user):
    await login(client)
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_login_is_rate_limited(client, user):
    codes = [(await login(client, password="nope")).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
