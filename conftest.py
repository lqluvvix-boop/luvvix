import os
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["SMTP_HOST"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core import email as email_module  # noqa: E402
from app.main import app  # noqa: E402

SENT: dict[str, str] = {}


@pytest.fixture(scope="session")
def client():
    email_module.send_code = lambda to, code, purpose: SENT.__setitem__(to, code)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def login_as(client, login: str, password: str, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"login": login, "password": password})
    assert r.status_code == 200, r.text
    ch = r.json()
    r = client.post("/api/v1/auth/verify", json={"challenge_id": ch["challenge_id"], "code": SENT[email]})
    assert r.status_code == 200, r.text
    return r.json()


def auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
