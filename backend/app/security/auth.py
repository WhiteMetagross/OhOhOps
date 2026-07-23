import hmac
import hashlib
import logging
from fastapi import Security, HTTPException, Request, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from app.core.config import get_settings

logger = logging.getLogger("ohohops.security.auth")

class AuthContext(BaseModel):
    namespace: str | None = None

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(request: Request, api_key: str = Security(api_key_header)) -> AuthContext:
    """
    Dependency to verify the Authorization header or x-api-key matches the configured ohohops_api_key,
    or resolves a SaaS key via ApiKeyService.
    Extracts the key if passed as 'Bearer <token>' or raw.
    """
    settings = get_settings()
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing Authentication Token")
        
    # Handle optional Bearer prefix
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()
        
    if api_key.startswith("oh_ops_"):
        ledger = getattr(request.app.state, "ledger", None)
        if not ledger:
            logger.error("Ledger not configured; cannot resolve SaaS keys.")
            raise HTTPException(status_code=401, detail="Authentication unavailable")
            
        from app.services.api_keys import ApiKeyService
        key_svc = ApiKeyService(ledger)
        namespace = await key_svc.resolve_key(api_key)
        
        if not namespace:
            logger.warning("Failed SaaS API key authentication attempt")
            raise HTTPException(status_code=401, detail="Invalid Authentication Token")
            
        return AuthContext(namespace=namespace)
        
    if not hmac.compare_digest(api_key, settings.ohohops_api_key):
        logger.warning("Failed API key authentication attempt")
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")
        
    return AuthContext(namespace=None)

async def verify_webhook_signature(request: Request, x_ohohops_signature: str = Header(None)):
    """
    Dependency to verify HMAC SHA-256 signature for incoming webhooks.
    """
    settings = get_settings()
    
    if not x_ohohops_signature:
        raise HTTPException(status_code=401, detail="Missing X-OhOhOps-Signature Header")
        
    body = await request.body()
    
    expected_signature = hmac.new(
        key=settings.ohohops_webhook_secret.encode('utf-8'),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_ohohops_signature, expected_signature):
        logger.warning("Failed webhook signature verification")
        raise HTTPException(status_code=401, detail="Invalid Webhook Signature")
        
    return True
