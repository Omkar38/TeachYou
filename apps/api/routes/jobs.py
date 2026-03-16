from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Iterator
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.auth import require_auth
from apps.api.schemas.jobs import (
    CreateJobRequest,
    CreateJobResponse,
    JobStatusResponse,
    LibraryJobItem,
    SegmentDetailResponse,
    SegmentUpdateRequest,
)
from db.models import Asset, Document, Event, Job, Segment

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_auth)])


def _json(obj) -> str:
    # Avoid optional binary deps (e.g., orjson) for easier local dev.
    return json.dumps(obj, ensure_ascii=False)


@router.post("", response_model=CreateJobResponse)
def create_job(payload: CreateJobRequest, db: Session = Depends(get_db)):
    doc = db.get(Document, payload.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    job_id = str(uuid.uuid4())
    if payload.layout == "reels":
        width, height = 720, 1280
    else:
        width, height = 1280, 720

    cfg = {
        "video_style": payload.video_style,
        "layout": payload.layout,
        "width": width,
        "height": height,
        "lang": "en",
    }
    job = Job(
        id=job_id,
        document_id=payload.document_id,
        mode=payload.mode,
        config=cfg,
        status="QUEUED",
        progress={"stage": "QUEUED"},
    )
    db.add(job)
    db.add(
        Event(
            id=str(uuid.uuid4()),
            job_id=job_id,
            event_type="JOB_CREATED",
            payload={"mode": payload.mode, **cfg},
        )
    )
    db.commit()

    # Dispatch worker job without importing pipeline module in API process
    try:
        from apps.worker.celery_app import celery_app
        celery_app.send_task("apps.worker.tasks.pipeline.run_job", args=[job_id])
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="WORKER_DISPATCHED", payload={}))
        db.commit()
    except Exception as e:
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="WORKER_DISPATCH_FAILED", payload={"error": str(e)}))
        db.commit()

    return CreateJobResponse(job_id=job_id)


@router.get("/library", response_model=list[LibraryJobItem])
def list_library(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=50)):
    """Last `limit` SUCCEEDED jobs, newest first."""
    jobs = (
        db.execute(
            select(Job)
            .where(Job.status == "SUCCEEDED")
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    items: list[LibraryJobItem] = []
    for j in jobs:
        doc = db.get(Document, j.document_id)
        assets = db.execute(select(Asset).where(Asset.job_id == j.id)).scalars().all()

        # try best-effort title extraction from outline.json
        title = None
        for a in assets:
            if a.type == "json" and (a.meta or {}).get("kind") == "outline" and a.uri:
                try:
                    obj = json.loads(Path(a.uri).read_text(encoding="utf-8"))
                    title = obj.get("title")
                except Exception:
                    title = None
                break
        if not title and doc and doc.filename:
            title = doc.filename

        thumb_asset_id = None
        video_asset_id = None
        duration_sec = None

        for a in assets:
            mk = (a.meta or {}).get("kind")
            if a.type == "video" and (mk in ("final_mp4", "whiteboard_mp4", "slideshow_mp4") or mk is None):
                video_asset_id = a.id
            if a.type in ("image", "thumbnail") and mk == "thumbnail":
                thumb_asset_id = a.id
            if mk == "video_meta" and isinstance((a.meta or {}).get("duration_sec"), (int, float)):
                duration_sec = float((a.meta or {}).get("duration_sec"))

        items.append(
            LibraryJobItem(
                id=j.id,
                document_id=j.document_id,
                mode=getattr(j, "mode", None),
                filename=getattr(doc, "filename", None),
                title=title,
                created_at=j.created_at,
                finished_at=j.finished_at,
                thumb_asset_id=thumb_asset_id,
                video_asset_id=video_asset_id,
                duration_sec=duration_sec,
            )
        )

    return items


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assets = db.execute(select(Asset).where(Asset.job_id == job_id)).scalars().all()
    artifacts: dict = {}
    for a in assets:
        artifacts.setdefault(a.type, []).append(
            {"id": a.id, "uri": a.uri, "meta": a.meta or {}, "segment_id": getattr(a, "segment_id", None)}
        )

    segs = (
        db.execute(
            select(Segment)
            .where(Segment.job_id == job_id)
            .order_by(Segment.segment_index.asc())
        )
        .scalars()
        .all()
    )
    segments = [
        {
            "id": s.id,
            "segment_index": s.segment_index,
            "title": s.title,
            "objective": s.objective,
            "status": s.status,
            "duration_target_sec": float(getattr(s, "duration_target_sec", 0.0) or 0.0),
        }
        for s in segs
    ]

    return JobStatusResponse(
        id=job.id,
        document_id=job.document_id,
        mode=job.mode,
        status=job.status,
        config=getattr(job, "config", None) or {},
        progress=job.progress or {},
        artifacts=artifacts,
        segments=segments,
        created_at=getattr(job, "created_at", None),
        finished_at=getattr(job, "finished_at", None),
    )


@router.get("/{job_id}/segments/{segment_id}", response_model=SegmentDetailResponse)
def get_segment(job_id: str, segment_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    seg = db.get(Segment, segment_id)
    if not job or not seg or seg.job_id != job_id:
        raise HTTPException(status_code=404, detail="Segment not found")

    editor = {
        "script": getattr(seg, "script", "") or "",
        "script_override": getattr(seg, "script_override", "") or "",
        "scenegraph": getattr(seg, "scenegraph", None) or {},
        "scenegraph_override": getattr(seg, "scenegraph_override", None) or {},
    }
    return SegmentDetailResponse(
        id=seg.id,
        job_id=seg.job_id,
        segment_index=seg.segment_index,
        title=seg.title,
        objective=seg.objective,
        status=seg.status,
        duration_target_sec=float(getattr(seg, "duration_target_sec", 0.0) or 0.0),
        editor=editor,
    )


@router.patch("/{job_id}/segments/{segment_id}")
def update_segment(job_id: str, segment_id: str, payload: SegmentUpdateRequest, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    seg = db.get(Segment, segment_id)
    if not job or not seg or seg.job_id != job_id:
        raise HTTPException(status_code=404, detail="Segment not found")

    changed = False
    if payload.script_override is not None:
        seg.script_override = payload.script_override
        changed = True
    if payload.scenegraph_override is not None:
        seg.scenegraph_override = payload.scenegraph_override
        changed = True

    if changed:
        db.add(seg)
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="SEGMENT_UPDATED", payload={"segment_id": segment_id}))
        db.commit()
    return {"ok": True}


@router.post("/{job_id}/segments/{segment_id}/regenerate")
def regenerate_segment(job_id: str, segment_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    seg = db.get(Segment, segment_id)
    if not job or not seg or seg.job_id != job_id:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Dispatch selective regeneration: rerender 1 segment then re-stitch.
    try:
        from apps.worker.celery_app import celery_app
        celery_app.send_task("apps.worker.tasks.pipeline.regenerate_segment", args=[job_id, segment_id])
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="SEGMENT_REGEN_DISPATCHED", payload={"segment_id": segment_id}))
        db.commit()
    except Exception as e:
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="SEGMENT_REGEN_DISPATCH_FAILED", payload={"segment_id": segment_id, "error": str(e)}))
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True}


@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # remove files best-effort
    assets = db.execute(select(Asset).where(Asset.job_id == job_id)).scalars().all()
    for a in assets:
        try:
            if a.uri and os.path.exists(a.uri):
                os.remove(a.uri)
        except Exception:
            pass

    # remove job output directory
    try:
        from apps.api.settings import settings
        out_dir = os.path.join(settings.data_dir, "outputs", job_id)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir, ignore_errors=True)
    except Exception:
        pass

    # delete DB rows
    db.execute(select(Asset).where(Asset.job_id == job_id))
    for a in assets:
        db.delete(a)
    # events and segments are deleted via cascade in most DBs; do best-effort
    try:
        from db.models import Event, Segment
        for ev in db.execute(select(Event).where(Event.job_id == job_id)).scalars().all():
            db.delete(ev)
        for seg in db.execute(select(Segment).where(Segment.job_id == job_id)).scalars().all():
            db.delete(seg)
    except Exception:
        pass
    db.delete(job)
    db.commit()
    return {"ok": True}


@router.get("/{job_id}/stream")
def stream_job_events(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    def event_iter() -> Iterator[bytes]:
        last_seen = 0.0
        yield b"event: OPEN\ndata: {}\n\n"
        while True:
            # Ensure this long-lived session sees fresh rows.
            try:
                db.expire_all()
            except Exception:
                pass
            rows = db.execute(select(Event).where(Event.job_id == job_id).order_by(Event.created_at.asc())).scalars().all()

            for ev in rows:
                ts = ev.created_at.timestamp() if ev.created_at else 0.0
                if ts <= last_seen:
                    continue
                last_seen = ts
                payload = {"type": ev.event_type, "payload": ev.payload or {}, "ts": ts}
                yield f"event: {ev.event_type}\ndata: {_json(payload)}\n\n".encode("utf-8")

            time.sleep(1.0)

    return StreamingResponse(event_iter(), media_type="text/event-stream")
