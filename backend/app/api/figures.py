from fastapi import APIRouter, HTTPException, Request
from starlette.responses import RedirectResponse

from app.db.postgres import get_pool
from app.storage.s3 import get_public_url

router = APIRouter()


@router.get("/api/figures/{figure_id}")
async def get_figure(figure_id: str, request: Request):
    settings = request.app.state.settings
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT s3_key FROM figures WHERE id = $1", figure_id
    )
    if not row or not row["s3_key"]:
        raise HTTPException(status_code=404, detail="Figure not found")

    url = get_public_url(settings, row["s3_key"])
    return RedirectResponse(url=url)
