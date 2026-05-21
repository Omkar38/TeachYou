from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from core.storyboard.schema import Storyboard
from db.models import StoryboardRow, StoryboardVersion


def save(db: Session, storyboard: Storyboard) -> StoryboardRow:
    """Upsert a storyboard and snapshot the previous version before overwriting."""
    data = storyboard.model_dump(mode="json")
    now = datetime.utcnow()

    existing = db.get(StoryboardRow, storyboard.storyboard_id)
    if existing:
        _snapshot(db, existing, now)
        existing.data = data
        existing.version = storyboard.version
        existing.updated_at = now
        db.add(existing)
        return existing

    row = StoryboardRow(
        id=storyboard.storyboard_id,
        job_id=storyboard.job_id,
        data=data,
        version=storyboard.version,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    return row


def _snapshot(db: Session, row: StoryboardRow, now: datetime) -> None:
    db.add(StoryboardVersion(
        id=str(uuid.uuid4()),
        storyboard_id=row.id,
        data=row.data,
        created_at=now,
    ))


def get_by_id(db: Session, storyboard_id: str) -> Optional[Storyboard]:
    row = db.get(StoryboardRow, storyboard_id)
    if not row:
        return None
    return Storyboard.model_validate(row.data)


def get_by_job(db: Session, job_id: str) -> Optional[Storyboard]:
    row = db.query(StoryboardRow).filter(StoryboardRow.job_id == job_id).first()
    if not row:
        return None
    return Storyboard.model_validate(row.data)


def list_versions(db: Session, storyboard_id: str) -> list[StoryboardVersion]:
    return (
        db.query(StoryboardVersion)
        .filter(StoryboardVersion.storyboard_id == storyboard_id)
        .order_by(StoryboardVersion.created_at.desc())
        .all()
    )
