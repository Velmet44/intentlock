import json
from fastapi import APIRouter, Depends, HTTPException
from backend.app.auth import get_current_user
from backend.app.models import ExtractRequest, RewriteRequest, JudgeRequest, SaveDraftRequest, Atom, Verdict, RewriteResult
from backend.app.llm import LLMClient
from backend.app.prompts import ATOM_EXTRACT, REWRITE, JUDGE
from backend.app.validator import l1_check
from backend.app import db

router = APIRouter(prefix="/api", tags=["drafts"])

def _parse_json(s):
    s = s.strip()
    # strip code fences
    if s.startswith("```"):
        s = s.strip("`")
        if s.startswith("json"):
            s = s[4:]
    return json.loads(s)

@router.post("/extract")
async def extract(req: ExtractRequest, user=Depends(get_current_user)):
    llm = LLMClient()
    prompt = ATOM_EXTRACT.replace("{original}", req.text)
    raw = await llm.generate(prompt, temperature=0.0, json_mode=True)
    try:
        data = _parse_json(raw)
    except Exception:
        data = {"atoms": []}
    atoms = data.get("atoms", [])
    db.log_event(None, "extract", {"user": user, "count": len(atoms)})
    return {"atoms": atoms, "raw": raw}

@router.post("/rewrite")
async def rewrite(req: RewriteRequest, user=Depends(get_current_user)):
    llm = LLMClient()
    prompt = REWRITE.replace("{goal}", req.goal).replace("{original}", req.original)
    raw = await llm.generate(prompt, temperature=0.3, json_mode=True)
    try:
        data = _parse_json(raw)
    except Exception:
        data = {"rewrite": req.original, "changes": []}
    rewrite_text = data.get("rewrite", req.original)
    changes = data.get("changes", [])
    # L1
    atoms_dicts = [a.model_dump() if hasattr(a, "model_dump") else a for a in req.atoms]
    l1 = l1_check(req.original, rewrite_text, atoms_dicts)
    result = {
        "rewrite": rewrite_text,
        "changes": changes,
        "l1": l1,
        "raw": raw,
    }
    return result

@router.post("/judge")
async def judge(req: JudgeRequest, user=Depends(get_current_user)):
    llm = LLMClient()
    atoms_str = json.dumps([a.model_dump() if hasattr(a, "model_dump") else a for a in req.atoms])
    prompt = JUDGE.replace("{original}", req.original).replace("{rewrite}", req.rewrite).replace("{atoms}", atoms_str)
    raw = await llm.generate(prompt, temperature=0.0, json_mode=True)
    try:
        data = _parse_json(raw)
    except Exception:
        data = {"verdicts": []}
    verdicts = data.get("verdicts", [])
    # compute overall
    overall = "PASS"
    reasons = []
    for v in verdicts:
        st = v.get("status", "PRESERVED")
        atom = v.get("atom", "")
        if st == "LOST":
            # check if refusal/promise
            overall = "FAIL"
            reasons.append(f"LOST: {atom}")
        elif st == "WEAKENED":
            if overall != "FAIL":
                overall = "WARN"
            reasons.append(f"WEAKENED: {atom}")
    # L1 override
    atoms_dicts = [a.model_dump() if hasattr(a, "model_dump") else a for a in req.atoms]
    l1 = l1_check(req.original, req.rewrite, atoms_dicts)
    if not l1["passed"]:
        overall = "FAIL"
        reasons = l1["failures"] + reasons
    return {"verdicts": verdicts, "overall": overall, "reasons": reasons, "l1": l1, "raw": raw}

@router.post("/drafts")
async def create_draft(payload: dict, user=Depends(get_current_user)):
    # save pending draft
    import datetime
    conn = db.get_conn() if False else None
    from backend.app import db as d
    c = d.get_conn()
    c.execute(
        "INSERT INTO drafts(auth0_sub, mode, original, goal, rewrite, atoms_json, verdict, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (user, payload.get("mode", "A"), payload.get("original", ""), payload.get("goal", ""), payload.get("rewrite", ""), json.dumps(payload.get("atoms", [])), payload.get("verdict", "PASS"), "pending", d.now()),
    )
    c.commit()
    did = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.close()
    d.log_event(did, "draft_created", {"user": user})
    return {"id": did}

@router.get("/drafts")
async def list_drafts(user=Depends(get_current_user)):
    from backend.app import db as d
    c = d.get_conn()
    rows = c.execute("SELECT * FROM drafts WHERE auth0_sub=? ORDER BY id DESC", (user,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

@router.post("/save")
async def save_draft(req: SaveDraftRequest, user=Depends(get_current_user)):
    from backend.app import db as d
    from backend.app.connectors import gmail as gmailc
    c = d.get_conn()
    row = c.execute("SELECT * FROM drafts WHERE id=? AND auth0_sub=?", (req.draft_id, user)).fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=404, detail="draft not found")
    draft = dict(row)
    c.close()

    if not req.approved:
        d.log_event(req.draft_id, "decline", {"reason": req.decline_reason})
        # update status
        c = d.get_conn()
        c.execute("UPDATE drafts SET status='declined' WHERE id=?", (req.draft_id,))
        c.commit(); c.close()
        return {"status": "declined", "reason": req.decline_reason}

    # approval gate: FGA check for recipient (Mode B) if provided
    recipient = req.recipient or ""
    if recipient:
        ok = await gmailc.can_draft_to if False else None
        from backend.app import fga
        allowed = await fga.can_draft_to(user, recipient)
        d.log_event(req.draft_id, "fga_check", {"relation": "can_draft_to", "object": recipient, "allowed": allowed})
        if not allowed:
            return {"status": "blocked", "reason": "FGA: not allowed to draft to this contact"}

    # Token Vault exchange
    # need user access token; for dev mode we may not have it. Use empty -> mock returns mock token in MOCK_CONNECTORS
    user_token = ""  # in real flow, pass from frontend or session
    try:
        gmail_token = await gmailc.exchange_token_vault(user_token)
    except Exception as e:
        d.log_event(req.draft_id, "exchange_error", {"error": str(e)})
        return {"status": "error", "reason": str(e)}
    d.log_event(req.draft_id, "exchange", {"scope": "gmail.compose", "token_present": bool(gmail_token)})

    # create draft
    gmail_draft_id = await gmailc.create_gmail_draft(
        gmail_token,
        to=recipient or "me@example.com",
        subject=req.subject or "Draft",
        body=draft.get("rewrite", ""),
    )
    d.log_event(req.draft_id, "approve", {"gmail_draft_id": gmail_draft_id})

    c = d.get_conn()
    c.execute("UPDATE drafts SET status='approved', gmail_draft_id=? WHERE id=?", (gmail_draft_id, req.draft_id))
    c.commit(); c.close()
    return {"status": "approved", "gmail_draft_id": gmail_draft_id}

@router.post("/copy_only")
async def copy_only(payload: dict, user=Depends(get_current_user)):
    from backend.app import db as d
    did = payload.get("draft_id")
    if did:
        c = d.get_conn()
        c.execute("UPDATE drafts SET status='copied_only' WHERE id=?", (did,))
        c.commit(); c.close()
        d.log_event(did, "copied_only", {})
    return {"status": "copied_only"}
