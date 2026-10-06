def test_tag_creation_is_normalized_and_idempotent(alice):
    a = alice.post("/tags", json={"name": "React", "category": "ability"})
    b = alice.post("/tags", json={"name": " react ", "category": "ability"})
    assert a.status_code == 201 and a.json()["id"] == b.json()["id"]
    # same name in another category is a different tag
    c = alice.post("/tags", json={"name": "React", "category": "objective"})
    assert c.json()["id"] != a.json()["id"]
    listed = alice.get("/tags", params={"category": "ability", "q": "rea"}).json()
    assert [t["name"] for t in listed] == ["React"]


def test_update_profile_with_tags_and_portfolio(alice, tags):
    r = alice.put(
        "/users/me",
        json={
            "bio": "Backend dev",
            "region": "Zacatecas, MX",
            "timezone": "America/Mexico_City",
            "future_goals": "ETHGlobal 2027",
            "tags": [
                {"tag_id": tags["FastAPI"], "level": "advanced"},
                {"tag_id": tags["Startup"]},
            ],
            "hackathons": [{"name": "HackMTY", "year": 2025, "award": "Best Beginner Hack"}],
            "past_projects": [{"name": "Todo API", "url": "https://example.com"}],
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()["profile"]
    assert p["bio"] == "Backend dev" and p["future_goals"] == "ETHGlobal 2027"
    assert {(t["tag"]["name"], t["level"]) for t in p["tags"]} == {("FastAPI", "advanced"), ("Startup", None)}
    assert p["hackathons"][0]["award"] == "Best Beginner Hack"
    assert p["past_projects"][0]["name"] == "Todo API"


def test_partial_update_keeps_other_fields_and_lists_replace(alice, tags):
    alice.put("/users/me", json={"bio": "hi", "tags": [{"tag_id": tags["React"]}, {"tag_id": tags["FastAPI"]}]})
    r = alice.put("/users/me", json={"region": "MX", "tags": [{"tag_id": tags["React"], "level": "expert"}]})
    p = r.json()["profile"]
    assert p["bio"] == "hi" and p["region"] == "MX"
    assert [(t["tag"]["name"], t["level"]) for t in p["tags"]] == [("React", "expert")]
    r = alice.put("/users/me", json={"tags": []})
    assert r.json()["profile"]["tags"] == []


def test_profile_validation(alice, bob):
    assert alice.put("/users/me", json={"timezone": "Mars/Olympus"}).status_code == 422
    assert alice.put("/users/me", json={"tags": [{"tag_id": 9999}]}).status_code == 422
    assert alice.put("/users/me", json={"username": "bob"}).status_code == 409
    assert alice.put("/users/me", json={"username": "alice_dev"}).status_code == 200


def test_public_profile_hides_email(alice, bob):
    r = alice.get(f"/users/{bob.id}")
    assert r.status_code == 200 and r.json()["username"] == "bob" and "email" not in r.json()
    assert alice.get("/users/9999").status_code == 404
