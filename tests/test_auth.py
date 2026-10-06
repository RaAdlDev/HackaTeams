def test_register_creates_user_and_empty_profile(client, alice):
    me = alice.get("/users/me").json()
    assert me["email"] == "alice@example.com"
    assert me["profile"]["username"] == "alice"
    assert me["profile"]["tags"] == [] and me["profile"]["hackathons"] == []
    assert "hashed_password" not in me


def test_duplicate_email_or_username_rejected(client, alice):
    base = {"password": "supersecret1"}
    r = client.post("/auth/register", json={"email": "ALICE@example.com", "username": "other", **base})
    assert r.status_code == 409
    r = client.post("/auth/register", json={"email": "new@example.com", "username": "ALICE", **base})
    assert r.status_code == 409


def test_register_validation(client):
    r = client.post("/auth/register", json={"email": "x@example.com", "username": "ab", "password": "supersecret1"})
    assert r.status_code == 422
    r = client.post("/auth/register", json={"email": "x@example.com", "username": "okname", "password": "short"})
    assert r.status_code == 422


def test_login_wrong_password_and_unknown_user(client, alice):
    assert client.post("/auth/token", data={"username": "alice@example.com", "password": "nope-nope"}).status_code == 401
    assert client.post("/auth/token", data={"username": "ghost@example.com", "password": "supersecret1"}).status_code == 401


def test_protected_routes_need_a_valid_token(client, alice):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/projects/feed").status_code == 401


def test_long_passwords_are_supported(client):
    pw = "p" * 120
    assert client.post("/auth/register", json={"email": "l@example.com", "username": "longpw", "password": pw}).status_code == 201
    assert client.post("/auth/token", data={"username": "l@example.com", "password": pw}).status_code == 200
