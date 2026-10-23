import os
import httpx
from backend.app.config import config

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"

async def exchange_token_vault(user_access_token: str, scopes: list[str] = None) -> str:
    """Exchange the user's Auth0 access token for a short-lived Gmail token via Token Vault (auth0-ai SDK)."""
    if config.MOCK_CONNECTORS:
        return "mock-gmail-token"
    scopes = scopes or config.GMAIL_SCOPES
    # normalize scope names: config uses gmail.read; Token Vault expects full scope URLs? Gmail scopes are full URLs.
    full_scopes = []
    for s in scopes:
        if s.startswith("https://"):
            full_scopes.append(s)
        elif s == "gmail.read":
            full_scopes.append("https://www.googleapis.com/auth/gmail.readonly")
        elif s == "gmail.compose":
            full_scopes.append("https://www.googleapis.com/auth/gmail.compose")
        else:
            full_scopes.append(s)
    from auth0_ai.authorizers.token_vault_authorizer import (
        TokenVaultAuthorizerParams, TokenVaultAuthorizerBase, _run_with_local_storage,
    )
    params = TokenVaultAuthorizerParams(
        scopes=full_scopes,
        connection=config.TOKEN_VAULT_CONNECTION,
        access_token=user_access_token,
    )
    authorizer = TokenVaultAuthorizerBase(params, config={
        "domain": config.AUTH0_DOMAIN,
        "client_id": config.AUTH0_CLIENT_ID,
        "client_secret": config.AUTH0_CLIENT_SECRET,
    })
    local_store = {
        "context": None,
        "scopes": full_scopes,
        "connection": config.TOKEN_VAULT_CONNECTION,
        "authorization_params": None,
    }
    async with _run_with_local_storage(local_store):
        resp = await authorizer.get_access_token_impl()
        if not resp:
            raise RuntimeError("Token Vault exchange returned no token")
        return resp["access_token"]

async def create_gmail_draft(access_token: str, to: str, subject: str, body: str) -> str:
    """Create a draft in Gmail (compose scope). Returns draft id."""
    if config.MOCK_CONNECTORS:
        return "mock-draft-id"
    import base64
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{GMAIL_API}/users/me/drafts",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"message": {"raw": raw}},
        )
        r.raise_for_status()
        return r.json().get("id", "")

async def list_inbox_messages(access_token: str, max_results: int = 10):
    if config.MOCK_CONNECTORS:
        return [
            {"id": "m1", "from": "manager@example.com", "subject": "Q3 report", "snippet": "Can you send the Q3 report by Friday?"},
            {"id": "m2", "from": "vendor@example.com", "subject": "Invoice", "snippet": "Please confirm the $1,240 invoice."},
        ]
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{GMAIL_API}/users/me/messages", headers={"Authorization": f"Bearer {access_token}"}, params={"maxResults": max_results, "q": "in:inbox"})
        r.raise_for_status()
        msgs = r.json().get("messages", [])
        out = []
        for m in msgs:
            dr = await c.get(f"{GMAIL_API}/users/me/messages/{m['id']}", headers={"Authorization": f"Bearer {access_token}"}, params={"format": "metadata", "metadataHeaders": ["From", "Subject"]})
            if dr.status_code != 200:
                continue
            d = dr.json()
            headers = {h["name"]: h["value"] for h in d.get("payload", {}).get("headers", [])}
            out.append({"id": m["id"], "from": headers.get("From", ""), "subject": headers.get("Subject", ""), "snippet": d.get("snippet", "")})
        return out

async def get_message(access_token: str, msg_id: str):
    if config.MOCK_CONNECTORS:
        return {"id": msg_id, "from": "manager@example.com", "subject": "Q3 report", "body": "Can you send the Q3 report by Friday?"}
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{GMAIL_API}/users/me/messages/{msg_id}", headers={"Authorization": f"Bearer {access_token}"}, params={"format": "full"})
        r.raise_for_status()
        d = r.json()
        # extract plain text body
        body = ""
        payload = d.get("payload", {})
        parts = payload.get("parts", [])
        if not parts:
            import base64
            data = payload.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode(errors="replace")
        else:
            for p in parts:
                if p.get("mimeType") == "text/plain":
                    import base64
                    data = p.get("body", {}).get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode(errors="replace")
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        return {"id": msg_id, "from": headers.get("From", ""), "subject": headers.get("Subject", ""), "body": body}
