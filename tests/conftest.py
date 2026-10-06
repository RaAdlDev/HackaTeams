
import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite://")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class Account:
    def __init__(self, client: TestClient, email: str, username: str):
        self.client = client
        self.email, self.username = email, username
        r = client.post(
            "/auth/register",
            json={"email": email, "username": username, "password": "supersecret1"},
        )
        assert r.status_code == 201, r.text
        self.id = r.json()["id"]
        r = client.post("/auth/token", data={"username": email, "password": "supersecret1"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def get(self, url, **kw):
        return self.client.get(url, headers=self.headers, **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self.headers, **kw)

    def put(self, url, **kw):
        return self.client.put(url, headers=self.headers, **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, headers=self.headers, **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, headers=self.headers, **kw)


@pytest.fixture
def make_account(client):
    def _make(name: str) -> Account:
        return Account(client, f"{name}@example.com", name)

    return _make


@pytest.fixture
def alice(make_account):
    return make_account("alice")


@pytest.fixture
def bob(make_account):
    return make_account("bob")


@pytest.fixture
def tags(alice):
    """A small controlled vocabulary, created through the API. Returns {name: id}."""
    spec = [
        ("FastAPI", "ability"), ("React", "ability"), ("Postgres", "ability"),
        ("Startup", "objective"), ("Open Source", "objective"),
        ("Beginner", "expertise"),
    ]
    out = {}
    for name, category in spec:
        r = alice.post("/tags", json={"name": name, "category": category})
        assert r.status_code == 201, r.text
        out[name] = r.json()["id"]
    return out


APPLY = {
    "hours_per_week": 10,
    "timezone": "America/Mexico_City",
    "abilities": "FastAPI, Postgres",
    "value_pitch": "I will build and own the whole backend and ship the MVP in two weeks.",
    "reward_type": "learning",
}
