from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.models.schemas import TranslateRequest

router = APIRouter()


@router.post("/api/translate")
async def translate(req: TranslateRequest, request: Request):
    engine = request.app.state.translation_engine

    async def event_generator():
        async for chunk in engine.translate_stream(req):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
