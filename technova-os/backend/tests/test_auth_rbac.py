from tests.conftest import register, auth_header


def test_first_user_is_super_admin(client):
    r = register(client, "boss@technova.club", "Boss")
    assert r.status_code == 201
    h = auth_header(client, "boss@technova.club")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role"] == "SUPER_ADMIN"


def test_second_user_is_member(client):
    register(client, "member1@technova.club", "Member One")
    h = auth_header(client, "member1@technova.club")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role"] == "MEMBER"


def test_duplicate_email_rejected(client):
    register(client, "dup@technova.club", "Dup")
    r = register(client, "dup@technova.club", "Dup2")
    assert r.status_code == 409


def test_short_password_rejected(client):
    r = client.post("/api/auth/register",
                    json={"email": "x@technova.club", "name": "X", "password": "short"})
    assert r.status_code == 422


def test_wrong_password_rejected(client):
    register(client, "logintest@technova.club", "L")
    r = client.post("/api/auth/login", data={"username": "logintest@technova.club", "password": "wrongpass"})
    assert r.status_code == 401


def test_unauthenticated_blocked(client):
    r = client.get("/api/me/profile")
    assert r.status_code == 401


def test_rbac_member_cannot_create_event(client):
    register(client, "rbac_member@technova.club", "Member RBAC")
    h = auth_header(client, "rbac_member@technova.club")
    r = client.post("/api/events", headers=h, json={
        "title": "Nope", "starts_at": "2030-01-01T10:00:00Z"})
    assert r.status_code == 403


def test_rbac_admin_can_create_event(client):
    h = auth_header(client, "boss@technova.club")  # super admin from first test
    r = client.post("/api/events", headers=h, json={
        "title": "Admin Event", "starts_at": "2030-01-01T10:00:00Z"})
    assert r.status_code == 201


def test_role_escalation_blocked(client):
    # a member cannot be promoted by someone at same/lower rank; only club_head+ can
    h_admin = auth_header(client, "boss@technova.club")
    members = client.get("/api/admin/members", headers=h_admin).json()
    target = next(m for m in members if m["email"] == "member1@technova.club")
    # super admin CAN promote
    r = client.post(f"/api/admin/members/{target['id']}/role", headers=h_admin, json={"role": "MENTOR"})
    assert r.status_code == 200
    # mentor cannot promote anyone to club_head (at/above own rank)
    h_mentor = auth_header(client, "member1@technova.club")
    r2 = client.post(f"/api/admin/members/{target['id']}/role", headers=h_mentor, json={"role": "CLUB_HEAD"})
    assert r2.status_code == 403
