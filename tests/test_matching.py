from tests.test_projects_applications import make_project


def setup_users(make_account, tags, alice):
    """alice: FastAPI+React+Startup. dev1 shares 3, dev2 shares 1, dev3 shares 0."""
    users = {"alice": alice}
    alice.put("/users/me", json={"tags": [{"tag_id": tags[t]} for t in ("FastAPI", "React", "Startup")]})
    layout = {
        "dev1": ["FastAPI", "React", "Startup", "Postgres"],
        "dev2": ["Startup", "Beginner"],
        "dev3": ["Open Source"],
    }
    regions = {"dev1": "Mexico", "dev2": "Spain", "dev3": "Mexico"}
    for name, tag_names in layout.items():
        acct = make_account(name)
        acct.put("/users/me", json={"region": regions.get(name), "tags": [{"tag_id": tags[t]} for t in tag_names]})
        users[name] = acct
    return users


def test_users_ranked_by_shared_tags(make_account, alice, tags):
    users = setup_users(make_account, tags, alice)
    feed = users["alice"].get("/users/browse").json()
    assert [(f["profile"]["username"], f["match_score"]) for f in feed] == [("dev1", 3), ("dev2", 1), ("dev3", 0)]
    assert {t["name"] for t in feed[0]["shared_tags"]} == {"FastAPI", "React", "Startup"}
    assert feed[2]["shared_tags"] == []
    assert all(f["profile"]["username"] != "alice" for f in feed)


def test_user_filters(make_account, alice, tags):
    me = setup_users(make_account, tags, alice)["alice"]
    names = lambda params: [f["profile"]["username"] for f in me.get("/users/browse", params=params).json()]
    assert names({"region": "mex"}) == ["dev1", "dev3"]
    assert names({"min_overlap": 1}) == ["dev1", "dev2"]
    assert names({"tag_ids": [tags["Open Source"]]}) == ["dev3"]
    assert names({"q": "dev2"}) == ["dev2"]
    assert names({"limit": 1, "offset": 1}) == ["dev2"]


def test_swiped_users_leave_the_feed(make_account, alice, tags):
    me = setup_users(make_account, tags, alice)["alice"]
    me.put("/users/me", json={"tags": [{"tag_id": tags["FastAPI"]}]})
    ids = {f["profile"]["username"]: f["profile"]["user_id"] for f in me.get("/users/browse").json()}
    me.post("/swipes", json={"target_user_id": ids["dev1"], "action": "pass"})
    assert "dev1" not in [f["profile"]["username"] for f in me.get("/users/browse").json()]


def test_projects_ranked_for_the_viewer(make_account, alice, tags):
    owner = make_account("owner")
    make_project(owner, tags, title="Perfect fit", tag_ids=[tags["FastAPI"], tags["React"]])
    make_project(owner, tags, title="Partial fit", tag_ids=[tags["React"], tags["Open Source"]])
    make_project(owner, tags, title="No overlap", tag_ids=[tags["Open Source"]])
    make_project(alice, tags, title="Mine")
    alice.put("/users/me", json={"tags": [{"tag_id": tags["FastAPI"]}, {"tag_id": tags["React"]}]})

    feed = alice.get("/projects/browse").json()
    assert [(f["project"]["title"], f["match_score"]) for f in feed] == [
        ("Perfect fit", 2), ("Partial fit", 1), ("No overlap", 0),
    ]
    assert {t["name"] for t in feed[0]["shared_tags"]} == {"FastAPI", "React"}
    assert alice.get("/projects/browse", params={"min_overlap": 2}).json()[0]["project"]["title"] == "Perfect fit"


def test_applied_and_swiped_projects_leave_project_browse(make_account, alice, tags):
    owner = make_account("owner")
    from tests.conftest import APPLY
    p1 = make_project(owner, tags, title="One")
    p2 = make_project(owner, tags, title="Two")
    p3 = make_project(owner, tags, title="Three")
    alice.post(f"/projects/{p1['id']}/apply", json=APPLY)
    alice.post("/swipes", json={"target_project_id": p2["id"], "action": "pass"})
    assert [f["project"]["title"] for f in alice.get("/projects/browse").json()] == ["Three"]


def test_owner_can_rank_developers_against_a_project(make_account, alice, tags):
    users = setup_users(make_account, tags, alice)
    p = make_project(alice, tags, tag_ids=[tags["Open Source"]])
    feed = alice.get("/users/browse", params={"for_project_id": p["id"]}).json()
    assert feed[0]["profile"]["username"] == "dev3" and feed[0]["match_score"] == 1
    assert users["dev1"].get("/users/browse", params={"for_project_id": p["id"]}).status_code == 403
    assert alice.get("/users/browse", params={"for_project_id": 9999}).status_code == 404
