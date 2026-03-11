import os

import aiosqlite
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/api/figures/{figure_id}")
async def get_figure(figure_id: str, request: Request):
    settings = request.app.state.settings
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT filepath FROM figures WHERE id = ?", (figure_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Figure not found")

    filepath = row["filepath"]
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Figure file missing from disk")

    return FileResponse(filepath, media_type="image/png")
