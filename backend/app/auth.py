import httpx
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from backend.app.config import config

bearer = HTTPBearer(auto_error=False)

_jwks_cache = None

async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    if not config.AUTH0_DOMAIN:
        return None
    url = f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient() as c:
        r = await c.get(url)
        r.raise_for_status()
        _jwks_cache = r.json()
        return _jwks_cache

async def get_current_user(creds: HTTPAuthorizationCredentials = Security(bearer)):
    if not config.AUTH0_DOMAIN:
        # dev mode: accept no token
        return "dev|local"
    if not creds:
        raise HTTPException(status_code=401, detail="missing token")
    token = creds.credentials
    jwks = await _jwks()
    try:
        unverified = jwt.get_unverified_header(token)
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == unverified.get("kid"):
                key = k
                break
        if key is None:
            raise HTTPException(status_code=401, detail="unknown kid")
        payload = jwt.decode(
            token,
            key,
            algorithms=config.AUTH0_ALGORITHMS,
            audience=config.AUTH0_AUDIENCE,
            issuer=f"https://{config.AUTH0_DOMAIN}/",
        )
        return payload.get("sub")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))
