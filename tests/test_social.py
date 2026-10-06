from tests.test_projects_applications import make_project


def test_mutual_like_between_developers_creates_match(alice, bob):
    r = alice.post("/swipes", json={"target_user_id": bob.id, "action": "like"})
    assert r.json() == {"action": "like", "matched": False}
    assert bob.get("/notifications").json() == []          # one-sided like stays silent

    r = bob.post("/swipes", json={"target_user_id": alice.id, "action": "like"})
    assert r.json()["matched"] is True
    for acct, other in ((alice, "bob"), (bob, "alice")):
        n = acct.get("/notifications").json()
        assert n[0]["type"] == "new_match" and n[0]["payload"]["username"] == other

    # re-liking does not duplicate notifications
    bob.post("/swipes", json={"target_user_id": alice.id, "action": "like"})
    assert len(alice.get("/notifications").json()) == 1


def test_changing_your_mind_updates_the_swipe(alice, bob):
    alice.post("/swipes", json={"target_user_id": bob.id, "action": "pass"})
    assert alice.post("/swipes", json={"target_user_id": bob.id, "action": "like"}).status_code == 200


def test_swipe_validation(alice, bob, tags):
    assert alice.post("/swipes", json={"target_user_id": alice.id, "action": "like"}).status_code == 400
    assert alice.post("/swipes", json={"target_user_id": 9999, "action": "like"}).status_code == 404
    assert alice.post("/swipes", json={"action": "like"}).status_code == 422
    p = make_project(alice, tags)
    assert alice.post("/swipes", json={"target_user_id": bob.id, "target_project_id": p["id"], "action": "like"}).status_code == 422
    assert alice.post("/swipes", json={"target_project_id": p["id"], "action": "like"}).status_code == 400


def test_liking_a_project_notifies_owner_and_matches_if_owner_liked_back(alice, bob, tags):
    p = make_project(alice, tags)
    r = bob.post("/swipes", json={"target_project_id": p["id"], "action": "like"})
    assert r.json()["matched"] is False
    assert alice.get("/notifications").json()[0]["type"] == "project_interest"

    # now the owner likes bob, then bob re-engages with another project of hers
    alice.post("/swipes", json={"target_user_id": bob.id, "action": "like"})
    p2 = make_project(alice, tags, title="Second project")
    r = bob.post("/swipes", json={"target_project_id": p2["id"], "action": "like"})
    assert r.json()["matched"] is True
    assert bob.get("/notifications").json()[0]["type"] == "new_match"


def test_notifications_read_state_is_private(alice, bob):
    bob.post("/swipes", json={"target_user_id": alice.id, "action": "like"})
    alice.post("/swipes", json={"target_user_id": bob.id, "action": "like"})
    n = alice.get("/notifications").json()[0]
    assert bob.post(f"/notifications/{n['id']}/read").status_code == 404
    assert alice.post(f"/notifications/{n['id']}/read").json()["is_read"] is True
    assert alice.get("/notifications", params={"unread_only": True}).json() == []
    bob.post("/notifications/read-all")
    assert bob.get("/notifications", params={"unread_only": True}).json() == []


def test_ads_board(alice, bob, tags):
    p = make_project(alice, tags)
    r = alice.post("/posts", json={"type": "cofounder_wanted", "title": "Need a co-founder", "body": "Looking for a React dev.", "project_id": p["id"]})
    assert r.status_code == 201 and r.json()["author"]["username"] == "alice"
    bob.post("/posts", json={"type": "availability", "title": "Free this weekend", "body": "Available for any hackathon."})
    assert len(bob.get("/posts").json()) == 2
    assert [x["type"] for x in bob.get("/posts", params={"type": "availability"}).json()] == ["availability"]
    # cannot attach someone else's project
    assert bob.post("/posts", json={"type": "project_idea", "title": "Stolen idea", "body": "Not my project at all.", "project_id": p["id"]}).status_code == 422
    # only the author can delete
    post_id = r.json()["id"]
    assert bob.delete(f"/posts/{post_id}").status_code == 403
    assert alice.delete(f"/posts/{post_id}").status_code == 204
    assert len(alice.get("/posts").json()) == 1
