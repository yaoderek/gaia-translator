from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.auth import get_current_user_id_optional
from app.db.postgres import get_pool
from app.models.schemas import TranslateRequest

router = APIRouter()


@router.post("/api/translate")
async def translate(
    req: TranslateRequest,
    request: Request,
    user_id: str | None = Depends(get_current_user_id_optional),
):
    engine = request.app.state.translation_engine
    target_persona = None
    if user_id:
        pool = get_pool()
        row = await pool.fetchrow(
            """SELECT discipline, bio, tags,
                      papers_of_interest, concepts_focus, methods_focus, tech_stack
                 FROM personas WHERE user_id = $1""",
            user_id,
        )
        if row:
            persona = {k: (row[k] or "") for k in (
                "discipline", "bio", "tags",
                "papers_of_interest", "concepts_focus", "methods_focus", "tech_stack",
            )}
            # Only treat as "active" persona if at least one signal field is non-empty.
            if any(persona[k].strip() for k in (
                "bio", "tags", "papers_of_interest", "concepts_focus", "methods_focus", "tech_stack"
            )):
                target_persona = persona

    async def event_generator():
        async for chunk in engine.translate_stream(req, target_persona=target_persona):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
