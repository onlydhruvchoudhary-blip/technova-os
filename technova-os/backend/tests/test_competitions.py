"""Competition scoring -> ranking -> certificates + winner points, and rubric validation."""
import pytest
from app.seed import seed
from tests.conftest import register, auth_header


@pytest.fixture(scope="module", autouse=True)
def _seed():
    seed(reset=True)
    yield


def test_competition_full_flow(client):
    h_head = auth_header(client, "head@technova.club")   # CLUB_HEAD can create
    h_mentor = auth_header(client, "mentor@technova.club")  # MENTOR can judge

    # two contestants
    register(client, "cont1@technova.club", "Contestant One")
    register(client, "cont2@technova.club", "Contestant Two")
    h1 = auth_header(client, "cont1@technova.club")
    h2 = auth_header(client, "cont2@technova.club")

    comp = client.post("/api/competitions", headers=h_head, json={
        "title": "Spring Hackathon", "kind": "Hackathon", "rubric": []}).json()
    cid = comp["id"]

    # members cannot create competitions
    assert client.post("/api/competitions", headers=h1, json={"title": "x"}).status_code == 403

    # register entries
    e1 = client.post(f"/api/competitions/{cid}/register", headers=h1,
                     json={"team_name": "Alpha", "title": "AI Tutor", "summary": "s"}).json()
    e2 = client.post(f"/api/competitions/{cid}/register", headers=h2,
                     json={"team_name": "Beta", "title": "Smart Bin", "summary": "s"}).json()
    # duplicate registration blocked
    assert client.post(f"/api/competitions/{cid}/register", headers=h1,
                       json={"team_name": "Alpha2"}).status_code == 409

    # move to judging
    client.post(f"/api/competitions/{cid}/status?status=judging", headers=h_head)

    # rubric bounds enforced: over-max rejected
    bad = client.post(f"/api/competitions/entries/{e1['id']}/score", headers=h_mentor,
                      json={"scores": {"Innovation": 999}, "comment": ""})
    assert bad.status_code == 400
    # unknown criterion rejected
    bad2 = client.post(f"/api/competitions/entries/{e1['id']}/score", headers=h_mentor,
                       json={"scores": {"Nonsense": 5}, "comment": ""})
    assert bad2.status_code == 400
    # a plain member cannot judge
    assert client.post(f"/api/competitions/entries/{e1['id']}/score", headers=h1,
                       json={"scores": {"Innovation": 10}}).status_code == 403

    # valid scores: entry 1 higher than entry 2
    full = {"Innovation": 20, "Technical Quality": 25, "Usefulness": 20,
            "Design": 15, "Presentation": 10, "Documentation": 10}
    low = {k: 1 for k in full}
    assert client.post(f"/api/competitions/entries/{e1['id']}/score", headers=h_mentor,
                       json={"scores": full, "comment": "great"}).status_code == 200
    assert client.post(f"/api/competitions/entries/{e2['id']}/score", headers=h_mentor,
                       json={"scores": low, "comment": "ok"}).status_code == 200

    # close & rank -> winner gets certificate + points
    client.post(f"/api/competitions/{cid}/status?status=closed", headers=h_head)
    detail = client.get(f"/api/competitions/{cid}", headers=h_head).json()
    ranked = sorted(detail["entries"], key=lambda e: e["rank"])
    assert ranked[0]["rank"] == 1
    assert ranked[0]["title"] == "AI Tutor"  # higher score ranked first

    # winner received a "Competition Winner" certificate
    certs = client.get("/api/certificates/me", headers=h1).json()
    assert any(c["kind"] == "Competition Winner" for c in certs)
    # participant received a participation certificate
    certs2 = client.get("/api/certificates/me", headers=h2).json()
    assert any(c["kind"] == "Competition Participation" for c in certs2)
