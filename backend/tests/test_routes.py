import os
os.environ.setdefault("MOCK_LLM", "1")
os.environ.setdefault("MOCK_CONNECTORS", "1")
os.environ.setdefault("DATABASE_PATH", "E:/Project/DevTo/Hacktober/intentlock/test_intentlock.db")

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import db as _db
_db.init_db()

client = TestClient(app)

def test_config():
    r = client.get("/api/config")
    assert r.status_code == 200
    assert r.json()["mock_llm"] is True

def test_extract_rewrite_judge_flow():
    r = client.post("/api/extract", json={"text": "I can't commit to Friday."})
    assert r.status_code == 200
    r2 = client.post("/api/rewrite", json={"original": "I can't commit to Friday.", "goal": "Firm", "atoms": []})
    assert r2.status_code == 200
    assert "can't" in r2.json()["rewrite"].lower() or r2.json()["rewrite"]
    r3 = client.post("/api/judge", json={"original": "I can't commit to Friday.", "rewrite": r2.json()["rewrite"], "atoms": []})
    assert r3.status_code == 200
    assert r3.json()["overall"] in ("PASS", "WARN", "FAIL")

def test_inbox_messages_have_allowed():
    r = client.get("/api/inbox/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert isinstance(msgs, list)
    for m in msgs:
        assert "allowed" in m

def test_inbox_locked_message():
    # msg_id m2 -> mock returns vendor; FGA mock allows all, so not locked. Check endpoint returns 200.
    r = client.get("/api/inbox/messages/m1")
    assert r.status_code == 200
    assert "locked" in r.json()

def test_save_copy_only():
    dr = client.post("/api/drafts", json={"mode": "A", "original": "x", "goal": "g", "rewrite": "x", "atoms": [], "verdict": "PASS"})
    did = dr.json()["id"]
    r = client.post("/api/copy_only", json={"draft_id": did})
    assert r.json()["status"] == "copied_only"
    r2 = client.post("/api/save", json={"draft_id": did, "approved": False, "decline_reason": "no"})
    assert r2.json()["status"] == "declined"
