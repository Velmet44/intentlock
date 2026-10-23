import os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_no_gmail_send_in_codebase():
    for dirpath, _, files in os.walk(ROOT):
        if ".git" in dirpath:
            continue
        for f in files:
            if f.endswith((".py", ".js", ".html", ".env", ".txt")) and f not in ("test_security.py",):
                p = os.path.join(dirpath, f)
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                assert "gmail.send" not in content, f"gmail.send found in {p}"

def test_scopes_default_no_send():
    from backend.app.config import config
    for s in config.GMAIL_SCOPES:
        assert "send" not in s
