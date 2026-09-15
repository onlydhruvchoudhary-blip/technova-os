"""GitHub sync endpoint: repo URL parsing + graceful fallback when no repo is linked."""
from app.routers.projects import _parse_repo
from tests.conftest import auth_header, register


def test_parse_repo_variants():
    assert _parse_repo("https://github.com/pallets/flask") == ("pallets", "flask")
    assert _parse_repo("https://github.com/pallets/flask.git") == ("pallets", "flask")
    assert _parse_repo("git@github.com:owner/repo.git") == ("owner", "repo")
    assert _parse_repo("https://gitlab.com/x/y") is None
    assert _parse_repo("") is None


def test_github_endpoint_unlinked_is_graceful(client):
    """A project with no repo_url returns linked=False, never a 500."""
    register(client, "ghtest@technova.club")
    hdr = auth_header(client, "ghtest@technova.club")
    # create a project (no repo linked)
    r = client.post("/api/projects", json={
        "title": "No Repo Project", "problem": "p", "solution": "s",
        "required_skills": [], "tech": ["python"], "team_size": 3,
    }, headers=hdr)
    assert r.status_code == 201, r.text
    slug = r.json()["slug"]
    g = client.get(f"/api/projects/{slug}/github", headers=hdr)
    assert g.status_code == 200
    assert g.json()["linked"] is False


def test_github_endpoint_requires_auth(client):
    assert client.get("/api/projects/anything/github").status_code == 401
