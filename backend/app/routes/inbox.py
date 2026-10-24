from fastapi import APIRouter, Depends, HTTPException, Request
from backend.app.auth import get_current_user
from backend.app.connectors import gmail as gmailc
from backend.app import fga, db

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

def _raw_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    return ""

@router.get("/messages")
async def messages(request: Request, user=Depends(get_current_user)):
    token = _raw_token(request)
    msgs = await gmailc.list_inbox_messages(token)
    # annotate FGA allowed
    out = []
    for m in msgs:
        sender = m.get("from", "")
        # extract email
        import re
        email_match = re.search(r"<([^>]+)>", sender)
        email = email_match.group(1) if email_match else sender
        allowed = await fga.can_read_from(user, email)
        m["sender_email"] = email
        m["allowed"] = allowed
        out.append(m)
    return out

@router.get("/messages/{msg_id}")
async def message(msg_id: str, request: Request, user=Depends(get_current_user)):
    token = _raw_token(request)
    m = await gmailc.get_message(token, msg_id)
    sender = m.get("from", "")
    import re
    email_match = re.search(r"<([^>]+)>", sender)
    email = email_match.group(1) if email_match else sender
    allowed = await fga.can_read_from(user, email)
    db.log_event(None, "fga_check", {"relation": "can_read_from", "object": email, "allowed": allowed, "msg_id": msg_id})
    if not allowed:
        return {"locked": True, "reason": "I'm not allowed to open that one.", "from": sender, "subject": m.get("subject")}
    return {"locked": False, **m}

@router.get("/activity")
async def activity(user=Depends(get_current_user)):
    from backend.app import db as d
    c = d.get_conn()
    rows = c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100").fetchall()
    c.close()
    return [dict(r) for r in rows]
