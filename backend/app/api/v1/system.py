from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["system"])

@router.get("/system/mode")
async def get_system_mode():
    """Return runtime deployment mode and feature toggles."""
    settings = get_settings()
    
    return {
        "deployment_mode": settings.deployment_mode,
        "features": {
            "api_keys": settings.is_cloud,
            "local_ingest": settings.is_local
        }
    }
