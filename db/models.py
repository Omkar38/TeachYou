from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, ForeignKey, Float

from sqlalchemy.types import JSON

try:
    from sqlalchemy.dialects.postgresql import JSONB
except Exception:
    JSONB = None

# Use JSON everywhere; use JSONB only when running on Postgres
JSONType = JSON().with_variant(JSONB, "postgresql") if JSONB is not None else JSON()

class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    mode: Mapped[str] = mapped_column(String(16), default="quick")
    # V1.5: Job-level immutable config (layout, style, renderer settings, etc.)
    # Stored as JSON so we can evolve without DB migrations.
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    progress: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    segment_index: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(256), default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    script: Mapped[str] = mapped_column(Text, default="")
    # V1.5: editable overrides from UI ("click on text to edit")
    script_override: Mapped[str] = mapped_column(Text, default="")
    # V1.5: structured scene plan (SceneGraph) and optional override
    scenegraph: Mapped[dict] = mapped_column(JSONType, default=dict)
    scenegraph_override: Mapped[dict] = mapped_column(JSONType, default=dict)
    citations: Mapped[dict] = mapped_column(JSONType, default=list)
    key_terms: Mapped[dict] = mapped_column(JSONType, default=list)
    refs: Mapped[dict] = mapped_column(JSONType, default=list)
    duration_target_sec: Mapped[float] = mapped_column(Float, default=15.0)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    segment_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("segments.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(32))  # image|audio|video|caption|json
    uri: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
