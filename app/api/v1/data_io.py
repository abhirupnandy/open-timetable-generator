"""Excel data workbook endpoints: template, sample, export, import, clear."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.data_io.importer import import_workbook
from app.data_io.workbook import build_workbook, export_rows, workbook_bytes
from app.db.models import (
    AcademicGroup,
    Course,
    Faculty,
    GroupBlockedSlot,
    Room,
    School,
    SessionLock,
    Subject,
    TeachingAssignment,
    Unavailability,
)
from app.db.session import get_db

logger = logging.getLogger("timetable.import")

router = APIRouter(prefix="/data", tags=["Data import / export"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SAMPLE_PATH = Path(__file__).resolve().parents[3] / "samples" / "sample_data.xlsx"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

DATA_MODELS = (
    SessionLock,
    GroupBlockedSlot,
    Unavailability,
    TeachingAssignment,
    AcademicGroup,
    Subject,
    Room,
    Faculty,
    Course,
    School,
)


def _xlsx(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/template")
def download_template(blank: bool = False) -> Response:
    """Template with instructions, headers, dropdowns and highlighted example
    rows (a small institution that imports as-is). ``blank=true`` leaves out
    the examples."""

    return _xlsx(workbook_bytes(build_workbook(examples=not blank)), "timetable_data_template.xlsx")


@router.get("/sample")
def download_sample() -> FileResponse:
    """A filled-in example workbook (80 assignments)."""

    if not SAMPLE_PATH.exists():
        raise HTTPException(status_code=404, detail="Sample workbook is not available")
    return FileResponse(SAMPLE_PATH, media_type=XLSX, filename="timetable_data_sample.xlsx")


@router.get("/export")
def export_data(db: Session = Depends(get_db)) -> Response:
    """Current database contents in the template format (edit and re-import)."""

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    return _xlsx(workbook_bytes(build_workbook(export_rows(db))), f"timetable_data_{stamp}.xlsx")


@router.get("/summary")
def data_summary(db: Session = Depends(get_db)) -> dict[str, int]:
    return {
        model.__tablename__: db.scalar(select(func.count()).select_from(model)) or 0
        for model in reversed(DATA_MODELS)
    }


@router.post("/import")
async def import_data(request: Request, db: Session = Depends(get_db)) -> dict:
    """Upload a filled-in workbook as the raw request body.

    Returns ``{"ok": true, "counts": {...}}`` on success. On failure nothing
    is changed and ``issues`` lists every problem with sheet, row and column.
    """

    data = await request.body()

    if not data:
        raise HTTPException(status_code=400, detail="Upload an .xlsx file as the request body")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Workbook is larger than 20 MB")

    result = import_workbook(db, data)
    return result.as_dict()


@router.post("/clear")
def clear_data(db: Session = Depends(get_db)) -> dict[str, int]:
    """Delete all scheduling data (timetable run history is kept)."""

    db.query(AcademicGroup).update({AcademicGroup.parent_group_id: None})
    counts = {}
    for model in DATA_MODELS:
        counts[model.__tablename__] = db.execute(delete(model)).rowcount
    db.commit()
    logger.info("All scheduling data cleared: %s", counts)
    return counts
