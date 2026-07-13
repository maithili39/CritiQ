"""Registration, login, and account-lockout behavior."""

from app.core.config import settings


def test_register_returns_token(client):
    res = client.post("/api/auth/register", json={"email": "new@example.com", "password": "longenough1"})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "new@example.com"
    assert "access_token" in body


def test_register_normalizes_email_case(client):
    client.post("/api/auth/register", json={"email": "Mixed@Example.com", "password": "longenough1"})
    res = client.post("/api/auth/login", json={"email": "mixed@example.com", "password": "longenough1"})
    assert res.status_code == 200


def test_register_rejects_invalid_email(client):
    res = client.post("/api/auth/register", json={"email": "not-an-email", "password": "longenough1"})
    assert res.status_code == 400


def test_register_rejects_short_password(client):
    res = client.post("/api/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert res.status_code == 400


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "longenough1"}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


def test_login_with_correct_credentials(client, registered_user):
    res = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_with_wrong_password(client, registered_user):
    res = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_login_with_unknown_email(client):
    res = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever1"})
    assert res.status_code == 401


def test_me_requires_valid_token(client, registered_user):
    res = client.get("/api/auth/me", headers=registered_user["headers"])
    assert res.status_code == 200
    assert res.json()["email"] == registered_user["email"]


def test_me_rejects_missing_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code in (401, 422)  # 422 if FastAPI rejects the missing required header first


def test_me_rejects_garbage_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_account_locks_after_max_failed_attempts(client, registered_user):
    for _ in range(settings.AUTH_MAX_FAILED_ATTEMPTS):
        res = client.post(
            "/api/auth/login",
            json={"email": registered_user["email"], "password": "wrong-password"},
        )
        assert res.status_code == 401

    # One more attempt, even with the *correct* password, should now be locked out.
    locked = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert locked.status_code == 423
