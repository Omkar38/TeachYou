from __future__ import annotations

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from apps.api.settings import settings
from db.session import make_session_factory
from db.models import Event, Job

# SessionLocal, _engine = make_session_factory(settings.postgres_dsn)
SessionLocal, engine = make_session_factory(settings.database_dsn)


def db_session() -> Session:
    return SessionLocal()


def emit_event(db: Session, job_id: str, event_type: str, payload: dict | None = None):
    ev = Event(id=str(uuid.uuid4()), job_id=job_id, event_type=event_type, payload=payload or {})
    db.add(ev)


def set_job_status(db: Session, job_id: str, status: str, progress: dict | None = None):
    job = db.get(Job, job_id)
    if not job:
        return
    job.status = status
    if progress is not None:
        job.progress = progress
    db.add(job)
