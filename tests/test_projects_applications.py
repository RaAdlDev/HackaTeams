from tests.conftest import APPLY


def make_project(owner, tags, **extra):
    body = {
        "title": "Hackathon matchmaker",
        "description": "A platform that matches developers into teams.",
        "region": "LATAM",
        "tag_ids": [tags["FastAPI"], tags["Startup"]],
        "roles": [{"title": "Backend dev", "slots": 1}, {"title": "Designer", "slots": 2}],
        "start_date": "2026-11-01",
        "deadline": "2026-11-30",
        **extra,
    }
    r = owner.post("/projects/", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_publish_and_read_project(alice, bob, tags):
    p = make_project(alice, tags)
    assert p["status"] == "open" and p["owner"]["username"] == "alice"
    assert {t["name"] for t in p["tags"]} == {"FastAPI", "Startup"}
    assert [r["title"] for r in p["roles"]] == ["Backend dev", "Designer"]
    assert p["members"] == []
    assert bob.get(f"/projects/{p['id']}").status_code == 200
    assert bob.get("/projects/9999").status_code == 404


def test_project_validation(alice, tags):
    bad = {"title": "Valid title", "description": "A long enough description.", "start_date": "2026-12-01", "deadline": "2026-11-01"}
    assert alice.post("/projects/", json=bad).status_code == 422
    assert alice.post("/projects/", json={**bad, "start_date": None, "deadline": None, "tag_ids": [9999]}).status_code == 422


def test_only_owner_can_edit_and_closing_hides_from_feed(alice, bob, tags):
    p = make_project(alice, tags)
    assert bob.patch(f"/projects/{p['id']}", json={"title": "Hijacked"}).status_code == 403
    r = alice.patch(f"/projects/{p['id']}", json={"title": "Renamed", "tag_ids": [tags["React"]]})
    assert r.status_code == 200 and r.json()["title"] == "Renamed"
    assert [t["name"] for t in r.json()["tags"]] == ["React"]
    assert len(bob.get("/projects/feed").json()) == 1
    alice.patch(f"/projects/{p['id']}", json={"status": "closed"})
    assert bob.get("/projects/feed").json() == []
    assert bob.post(f"/projects/{p['id']}/apply", json=APPLY).status_code == 409


def test_feed_filters_and_pagination(alice, bob, tags):
    for i in range(3):
        make_project(alice, tags, title=f"Project {i}", region="Spain" if i == 0 else "LATAM")
    assert len(bob.get("/projects/feed").json()) == 3
    assert len(bob.get("/projects/feed", params={"limit": 2}).json()) == 2
    assert len(bob.get("/projects/feed", params={"limit": 2, "offset": 2}).json()) == 1
    assert [p["title"] for p in bob.get("/projects/feed", params={"region": "spain"}).json()] == ["Project 0"]
    assert len(bob.get("/projects/feed", params=[("tag_ids", tags["React"])]).json()) == 0
    # newest first
    assert bob.get("/projects/feed").json()[0]["title"] == "Project 2"


def test_roles_can_be_added_and_removed(alice, bob, tags):
    p = make_project(alice, tags)
    r = alice.post(f"/projects/{p['id']}/roles", json={"title": "QA"})
    assert r.status_code == 201
    assert bob.post(f"/projects/{p['id']}/roles", json={"title": "x"}).status_code == 403
    assert alice.delete(f"/projects/{p['id']}/roles/{r.json()['id']}").status_code == 204
    assert len(alice.get(f"/projects/{p['id']}").json()["roles"]) == 2


# ---- applications -----------------------------------------------------------

def test_application_requires_all_structured_fields(alice, bob, tags):
    p = make_project(alice, tags)
    for missing in ("hours_per_week", "timezone", "abilities", "value_pitch", "reward_type"):
        body = {k: v for k, v in APPLY.items() if k != missing}
        assert bob.post(f"/projects/{p['id']}/apply", json=body).status_code == 422, missing


def test_reward_rules_separate_payable_from_non_payable(alice, bob, tags):
    p = make_project(alice, tags)
    url = f"/projects/{p['id']}/apply"
    # flat fee must declare an amount (so it can be paid on-platform)
    assert bob.post(url, json={**APPLY, "reward_type": "flat_fee"}).status_code == 422
    # non-payable terms must not carry an amount
    assert bob.post(url, json={**APPLY, "reward_type": "equity", "reward_amount": "100"}).status_code == 422
    assert bob.post(url, json={**APPLY, "timezone": "Nowhere/City"}).status_code == 422
    assert bob.post(url, json={**APPLY, "hours_per_week": 0}).status_code == 422
    r = bob.post(url, json={**APPLY, "reward_type": "flat_fee", "reward_amount": "1500.50", "currency": "USD"})
    assert r.status_code == 201, r.text
    assert r.json()["is_payable"] is True and r.json()["reward_amount"] == "1500.50"


def test_apply_business_rules(alice, bob, tags):
    p = make_project(alice, tags)
    url = f"/projects/{p['id']}/apply"
    assert alice.post(url, json=APPLY).status_code == 400            # own project
    assert bob.post("/projects/9999/apply", json=APPLY).status_code == 404
    assert bob.post(url, json={**APPLY, "role_id": 9999}).status_code == 422
    assert bob.post(url, json=APPLY).status_code == 201
    assert bob.post(url, json=APPLY).status_code == 409              # only once


def test_accept_flow_adds_member_and_notifies(alice, bob, tags):
    p = make_project(alice, tags)
    role_id = p["roles"][0]["id"]
    app = bob.post(f"/projects/{p['id']}/apply", json={**APPLY, "role_id": role_id}).json()
    assert app["status"] == "pending"

    # owner got an "application received" notification
    n = alice.get("/notifications").json()
    assert n[0]["type"] == "application_received" and n[0]["payload"]["applicant_username"] == "bob"

    # inbox + permissions
    assert [a["id"] for a in alice.get(f"/projects/{p['id']}/applications").json()] == [app["id"]]
    assert bob.get(f"/projects/{p['id']}/applications").status_code == 403
    assert bob.patch(f"/applications/{app['id']}/status", json={"status": "accepted"}).status_code == 403
    assert alice.patch(f"/applications/{app['id']}/status", json={"status": "pending"}).status_code == 422

    r = alice.patch(f"/applications/{app['id']}/status", json={"status": "accepted"})
    assert r.status_code == 200 and r.json()["status"] == "accepted" and r.json()["decided_at"]

    members = alice.get(f"/projects/{p['id']}").json()["members"]
    assert [(m["username"], m["role"]["title"]) for m in members] == [("bob", "Backend dev")]

    n = bob.get("/notifications").json()
    assert n[0]["type"] == "application_accepted" and n[0]["payload"]["requires_payment"] is False

    # decisions are final
    assert alice.patch(f"/applications/{app['id']}/status", json={"status": "rejected"}).status_code == 409
    assert bob.post(f"/applications/{app['id']}/withdraw").status_code == 409


def test_accepting_payable_application_flags_payment(alice, bob, tags):
    p = make_project(alice, tags)
    app = bob.post(
        f"/projects/{p['id']}/apply",
        json={**APPLY, "reward_type": "flat_fee", "reward_amount": "800"},
    ).json()
    alice.patch(f"/applications/{app['id']}/status", json={"status": "accepted"})
    assert bob.get("/notifications").json()[0]["payload"]["requires_payment"] is True


def test_role_slots_are_enforced(alice, bob, make_account, tags):
    carol = make_account("carol")
    p = make_project(alice, tags)
    role_id = p["roles"][0]["id"]  # Backend dev, 1 slot
    a1 = bob.post(f"/projects/{p['id']}/apply", json={**APPLY, "role_id": role_id}).json()
    a2 = carol.post(f"/projects/{p['id']}/apply", json={**APPLY, "role_id": role_id}).json()
    assert alice.patch(f"/applications/{a1['id']}/status", json={"status": "accepted"}).status_code == 200
    assert alice.patch(f"/applications/{a2['id']}/status", json={"status": "accepted"}).status_code == 409
    assert alice.patch(f"/applications/{a2['id']}/status", json={"status": "rejected"}).status_code == 200


def test_withdraw_and_my_applications(alice, bob, tags):
    p = make_project(alice, tags)
    app = bob.post(f"/projects/{p['id']}/apply", json=APPLY).json()
    assert [a["id"] for a in bob.get("/applications/mine").json()] == [app["id"]]
    assert alice.post(f"/applications/{app['id']}/withdraw").status_code == 403
    assert alice.get(f"/applications/{app['id']}").status_code == 200   # owner may view
    assert bob.post(f"/applications/{app['id']}/withdraw").json()["status"] == "withdrawn"
