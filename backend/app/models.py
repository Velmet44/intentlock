from typing import List, Optional, Literal
from pydantic import BaseModel

AtomType = Literal["entity", "number", "ask", "refusal", "promise", "condition"]

class Atom(BaseModel):
    type: AtomType
    value: str
    evidence: str

class AtomList(BaseModel):
    atoms: List[Atom]

class Contract(BaseModel):
    atoms: List[Atom]
    goal: str

class VerdictItem(BaseModel):
    atom: str
    status: Literal["PRESERVED", "WEAKENED", "STRENGTHENED", "LOST"]
    note: str = ""

class Verdict(BaseModel):
    verdicts: List[VerdictItem]
    overall: Literal["PASS", "WARN", "FAIL"] = "PASS"
    reasons: List[str] = []

class RewriteResult(BaseModel):
    rewrite: str
    changes: List[str] = []

class DraftStatus(BaseModel):
    id: int
    auth0_sub: str
    mode: str = "A"
    original: str
    goal: str
    rewrite: str
    atoms_json: str
    verdict: str
    status: str = "pending"
    gmail_draft_id: Optional[str] = None
    created_at: str

class ExtractRequest(BaseModel):
    text: str

class RewriteRequest(BaseModel):
    original: str
    goal: str
    atoms: List[Atom]

class JudgeRequest(BaseModel):
    original: str
    rewrite: str
    atoms: List[Atom]

class SaveDraftRequest(BaseModel):
    draft_id: int
    approved: bool
    decline_reason: Optional[str] = None
    user_access_token: Optional[str] = None
    # Mode B thread context
    thread_id: Optional[int] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None
