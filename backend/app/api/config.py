"""Runtime config endpoint so the frontend can init Supabase without build-time env vars."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/api/config")
async def get_config():
    settings = get_settings()
    return {
        "supabase_url": settings.supabase_url,
        "supabase_anon_key": settings.supabase_anon_key,
    }
