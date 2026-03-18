import os, hmac
from fastapi import Header, HTTPException

async def require_api_key(x_api_key: str = Header(default="")):
    server_key = os.getenv("ASTRA_API_KEY", "")
    if not server_key:
        raise HTTPException(status_code=500, detail="ASTRA_API_KEY not configured on server")
    if not hmac.compare_digest(x_api_key, server_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
