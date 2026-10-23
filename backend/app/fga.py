import os
from typing import Optional
from backend.app.config import config

async def _client():
    if not config.FGA_STORE_ID:
        return None
    from openfga_sdk import OpenFgaClient, ClientConfiguration
    from openfga_sdk.credentials import Credentials, CredentialConfiguration
    cfg = ClientConfiguration(
        api_url=config.FGA_API_URL,
        store_id=config.FGA_STORE_ID,
        authorization_model_id=config.FGA_MODEL_ID or None,
        credentials=Credentials(
            method="client_credentials",
            configuration=CredentialConfiguration(
                api_issuer=config.FGA_API_TOKEN_ISSUER,
                api_audience=config.FGA_API_AUDIENCE,
                client_id=config.FGA_CLIENT_ID,
                client_secret=config.FGA_CLIENT_SECRET,
            ),
        ),
    )
    return OpenFgaClient(cfg)

async def fga_check(user_sub: str, relation: str, object_type: str, object_id: str) -> bool:
    """Generic FGA check. Returns True if allowed."""
    client = await _client()
    if client is None:
        # dev/mock: allow
        return True
    try:
        from openfga_sdk.client import ClientCheckRequest
        from openfga_sdk import ConsistencyPreference
        req = ClientCheckRequest(user=f"user:{user_sub}", relation=relation, object=f"{object_type}:{object_id}")
        async with client:
            resp = await client.check(req, {"consistency": ConsistencyPreference.HIGHER_CONSISTENCY})
            return bool(resp.allowed)
    except Exception:
        return False

async def can_read_from(user_sub: str, sender_email: str) -> bool:
    return await fga_check(user_sub, "can_read_from", "sender", sender_email)

async def can_draft_to(user_sub: str, contact_email: str) -> bool:
    return await fga_check(user_sub, "can_draft_to", "contact", contact_email)
