from tests.helpers import auth_headers


def test_register_returns_user_without_password(client):
    resp = client.post(
        "/auth/register", json={"email": "Bob@Example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "bob@example.com"
    assert "password" not in body and "hashed_password" not in body


def test_duplicate_email_is_rejected(client):
    payload = {"email": "bob@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_short_password_is_rejected(client):
    resp = client.post("/auth/register", json={"email": "bob@example.com", "password": "short"})
    assert resp.status_code == 422


def test_login_with_wrong_password_fails(client):
    auth_headers(client)
    resp = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401

    headers = auth_headers(client)
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"
