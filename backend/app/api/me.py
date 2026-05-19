"""Current user and persona endpoints."""

import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user_id
from app.core.config import get_settings
from app.db.postgres import get_pool
from app.models.schemas import PersonaUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def _decode_jwt_claims(request: Request) -> dict:
    """Return decoded JWT payload or empty dict if unavailable."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {}
    token = auth_header[7:]
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        return {}
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        return {}


@router.get("/api/me")
async def get_me(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Return current user id, email, username (from JWT metadata), and persona."""
    pool = get_pool()
    row = await pool.fetchrow(
        """SELECT username, discipline, bio, tags,
                  papers_of_interest, concepts_focus, methods_focus, tech_stack,
                  updated_at
             FROM personas WHERE user_id = $1""",
        user_id,
    )
    claims = _decode_jwt_claims(request)
    email = claims.get("email")
    user_metadata = claims.get("user_metadata") or {}
    jwt_username = user_metadata.get("username") or ""

    persona_username = (row["username"] or "") if row else ""
    display_username = persona_username or jwt_username

    persona = {
        "username": display_username,
        "discipline": (row["discipline"] or "") if row else "",
        "bio": (row["bio"] or "") if row else "",
        "tags": (row["tags"] or "") if row else "",
        "papers_of_interest": (row["papers_of_interest"] or "") if row else "",
        "concepts_focus": (row["concepts_focus"] or "") if row else "",
        "methods_focus": (row["methods_focus"] or "") if row else "",
        "tech_stack": (row["tech_stack"] or "") if row else "",
        "updated_at": str(row["updated_at"]) if row and row["updated_at"] else None,
    }

    return {
        "user_id": user_id,
        "email": email,
        "username": display_username,
        "persona": persona,
    }


@router.put("/api/me/persona")
async def update_persona(
    body: PersonaUpdate,
    user_id: str = Depends(get_current_user_id),
):
    """Create or update the current user's persona."""
    pool = get_pool()
    fields = (
        "username", "discipline", "bio", "tags",
        "papers_of_interest", "concepts_focus", "methods_focus", "tech_stack",
    )
    try:
        existing = await pool.fetchrow(
            f"SELECT {', '.join(fields)} FROM personas WHERE user_id = $1",
            user_id,
        )
    except Exception as e:
        logger.exception("Failed to read personas for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=503, detail=f"Database error reading persona: {e!s}") from e

    body_dict = body.model_dump()
    values = {
        name: (body_dict[name] if body_dict.get(name) is not None
               else (existing[name] if existing else "") or "")
        for name in fields
    }

    try:
        await pool.execute(
            """
            INSERT INTO personas (user_id, username, discipline, bio, tags,
                                  papers_of_interest, concepts_focus, methods_focus, tech_stack,
                                  updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                discipline = EXCLUDED.discipline,
                bio = EXCLUDED.bio,
                tags = EXCLUDED.tags,
                papers_of_interest = EXCLUDED.papers_of_interest,
                concepts_focus = EXCLUDED.concepts_focus,
                methods_focus = EXCLUDED.methods_focus,
                tech_stack = EXCLUDED.tech_stack,
                updated_at = NOW()
            """,
            user_id,
            values["username"],
            values["discipline"],
            values["bio"],
            values["tags"],
            values["papers_of_interest"],
            values["concepts_focus"],
            values["methods_focus"],
            values["tech_stack"],
        )
    except Exception as e:
        logger.exception("Failed to write persona for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=503, detail=f"Database error saving persona: {e!s}") from e

    return {"status": "ok"}
