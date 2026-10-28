import requests


def make_session(token):
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"
    session.verify = False
    return session


def list_projects(token):
    resp = make_session(token).get("https://internal.example.com/api/projects", timeout=10)
    resp.raise_for_status()
    return [p["name"] for p in resp.json()]
