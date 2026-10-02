from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def now_utc() -> datetime:
    return datetime.now(UTC)


def get_or_404(db: Session, model, object_id: int):
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} {object_id} not found")
    return obj


def require_exists(db: Session, model, object_id: int, field_name: str) -> None:
    if db.get(model, object_id) is None:
        raise HTTPException(status_code=404, detail=f"{field_name} {object_id} does not exist")


def commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Resource conflicts with existing data or references"
        ) from exc
