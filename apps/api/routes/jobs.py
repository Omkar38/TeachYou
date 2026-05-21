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
    BrollSearchRequest,
    CreateJobRequest,
    CreateJobResponse,
    JobStatusResponse,
    LibraryJobItem,
    SceneStylePatchRequest,
    SegmentDetailResponse,
    SegmentUpdateRequest,
    StoryboardEditRequest,
    StoryboardEditResponse,
)
from core.storyboard import store as storyboard_store
from db.models import Asset, Document, Event, Job, Segment

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_auth)])

_ASPECT_MAP = {"reels": "9:16", "landscape": "16:9", "laptop": "16:9", "square": "1:1"}
_DIM_MAP = {"reels": (720, 1280), "landscape": (1280, 720), "laptop": (1280, 720), "square": (720, 720)}


def _doc_path(document_id: str) -> str:
    from apps.api.settings import settings
    up = os.path.join(settings.data_dir, "uploads")
    pdf = os.path.join(up, f"{document_id}.pdf")
    if os.path.exists(pdf):
        return pdf
    txt = os.path.join(up, f"{document_id}.txt")
    return txt if os.path.exists(txt) else pdf


def _doc_extract_dir(document_id: str) -> str:
    from apps.api.settings import settings
    p = os.path.join(settings.data_dir, "extracted", document_id)
    os.makedirs(p, exist_ok=True)
    return p


def _read_document_text(document_id: str) -> str:
    in_path = _doc_path(document_id)
    if not os.path.exists(in_path):
        return ""
    if in_path.lower().endswith(".pdf"):
        try:
            from core.ingestion.pdf_extract import ingest_pdf
            manifest = ingest_pdf(in_path, _doc_extract_dir(document_id), max_pages=8, max_images=12)
            tp = manifest.get("text_path")
            if tp and Path(tp).exists():
                return Path(tp).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
        return ""
    return Path(in_path).read_text(encoding="utf-8", errors="ignore")


def _json(obj) -> str:
    # Avoid optional binary deps (e.g., orjson) for easier local dev.
    return json.dumps(obj, ensure_ascii=False)


@router.post("", response_model=CreateJobResponse)
def create_job(payload: CreateJobRequest, db: Session = Depends(get_db)):
    doc = db.get(Document, payload.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    job_id = str(uuid.uuid4())
    aspect_ratio = _ASPECT_MAP.get(payload.layout, "9:16")
    width, height = _DIM_MAP.get(payload.layout, (720, 1280))
    length_preset = payload.length_preset or ("30s" if payload.mode == "quick" else "3m")

    cfg = {
        "video_style": payload.video_style,
        "layout": payload.layout,
        "aspect_ratio": aspect_ratio,
        "length_preset": length_preset,
        "caption_style": payload.caption_style,
        "width": width,
        "height": height,
        "lang": "en",
    }
    job = Job(
        id=job_id,
        document_id=payload.document_id,
        mode=payload.mode,
        config=cfg,
        status="PLANNING",
        progress={"stage": "PLANNING"},
    )
    db.add(job)
    db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="JOB_CREATED", payload={"mode": payload.mode, **cfg}))
    db.commit()

    # Plan storyboard synchronously so user sees scenes immediately
    storyboard_dict = None
    try:
        from core.agents.supervisor import plan_storyboard

        text = _read_document_text(payload.document_id) or "(No extractable text.)"
        title = (doc.filename or "").rsplit(".", 1)[0] or ""

        storyboard = plan_storyboard(
            text=text,
            job_id=job_id,
            title=title,
            aspect_ratio=aspect_ratio,
            length_preset=length_preset,
            mode=payload.mode,
        )
        storyboard_store.save(db, storyboard)

        for scene in storyboard.scenes:
            db.add(Segment(
                id=str(uuid.uuid4()),
                job_id=job_id,
                segment_index=scene.order,
                title=scene.title,
                objective=scene.objective,
                script="",
                script_override=scene.script,
                citations=[],
                key_terms=[],
                status="PLANNED",
                duration_target_sec=float(scene.duration_s),
            ))

        job.status = "PLANNED"
        job.progress = {"stage": "PLANNED", "scenes": len(storyboard.scenes)}
        db.add(job)
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="PLAN_COMPLETE", payload={"scenes": len(storyboard.scenes)}))
        db.commit()
        storyboard_dict = storyboard.model_dump(mode="json")

    except Exception as e:
        # Planning failed — fall back to worker-driven flow
        job.status = "QUEUED"
        job.progress = {"stage": "QUEUED", "plan_error": str(e)}
        db.add(job)
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="PLAN_FAILED", payload={"error": str(e)}))
        db.commit()
        try:
            from apps.worker.celery_app import celery_app
            celery_app.send_task("apps.worker.tasks.pipeline.run_job", args=[job_id])
            db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="WORKER_DISPATCHED", payload={}))
            db.commit()
        except Exception:
            pass

    return CreateJobResponse(job_id=job_id, storyboard=storyboard_dict)


@router.post("/{job_id}/render")
def render_job(job_id: str, db: Session = Depends(get_db)):
    """Dispatch rendering for a PLANNED job. User calls this after reviewing the storyboard."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("PLANNED", "FAILED"):
        raise HTTPException(status_code=400, detail=f"Job is {job.status}; only PLANNED or FAILED jobs can be rendered")

    # Reset segment statuses so the worker picks them up
    segs = db.execute(select(Segment).where(Segment.job_id == job_id)).scalars().all()
    for seg in segs:
        seg.status = "QUEUED"
        db.add(seg)

    job.status = "QUEUED"
    job.progress = {"stage": "QUEUED"}
    db.add(job)
    db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="RENDER_REQUESTED", payload={}))
    db.commit()

    try:
        from apps.worker.celery_app import celery_app
        celery_app.send_task("apps.worker.tasks.pipeline.run_job", args=[job_id])
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="WORKER_DISPATCHED", payload={}))
        db.commit()
    except Exception as e:
        db.add(Event(id=str(uuid.uuid4()), job_id=job_id, event_type="WORKER_DISPATCH_FAILED", payload={"error": str(e)}))
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True}


@router.post("/{job_id}/edit", response_model=StoryboardEditResponse)
def edit_job_storyboard(job_id: str, payload: StoryboardEditRequest, db: Session = Depends(get_db)):
    """Magic Box: apply a natural-language instruction to the storyboard."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    sb = storyboard_store.get_by_job(db, job_id)
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not yet generated for this job")

    from core.agents.editor import edit_storyboard
    updated_sb, changes = edit_storyboard(sb, payload.instruction)

    if changes:
        updated_sb.version = (sb.version or 1) + 1
        storyboard_store.save(db, updated_sb)

        # Sync changed segment scripts/titles back to Segment rows
        for ch in changes:
            idx = ch.get("scene_index", -1)
            field = ch.get("field", "")
            value = ch.get("value")
            if idx < 0 or not isinstance(value, str):
                continue
            segs = db.execute(
                select(Segment)
                .where(Segment.job_id == job_id, Segment.segment_index == idx)
            ).scalars().all()
            for seg in segs:
                if field == "script":
                    seg.script_override = value
                elif field == "title":
                    seg.title = value
                elif field == "objective":
                    seg.objective = value
                db.add(seg)

        db.add(Event(
            id=str(uuid.uuid4()),
            job_id=job_id,
            event_type="STORYBOARD_EDITED",
            payload={"instruction": payload.instruction, "changes": len(changes)},
        ))
        db.commit()

    return StoryboardEditResponse(
        storyboard=updated_sb.model_dump(mode="json"),
        changes=changes,
        explanation="",
    )


@router.post("/{job_id}/scenes/{scene_index}/broll")
def search_scene_broll(
    job_id: str,
    scene_index: int,
    payload: BrollSearchRequest,
    db: Session = Depends(get_db),
):
    """Search Pexels/Pixabay for B-roll candidates for a scene and save them to the storyboard."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    sb = storyboard_store.get_by_job(db, job_id)
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    if scene_index < 0 or scene_index >= len(sb.scenes):
        raise HTTPException(status_code=404, detail="Scene index out of range")

    from apps.api.settings import settings
    from core.broll.search import search_broll

    scene = sb.scenes[scene_index]
    query = (payload.query or "").strip() or scene.title or scene.objective or "nature"
    cfg = getattr(job, "config", None) or {}
    aspect_ratio = str(cfg.get("aspect_ratio") or "9:16")

    candidates = search_broll(
        query=query,
        aspect_ratio=aspect_ratio,
        pexels_key=settings.pexels_api_key,
        pixabay_key=settings.pixabay_api_key,
        limit=settings.broll_results_per_scene,
    )

    if candidates:
        scene.media_candidates = candidates
        scene.selected_media_idx = 0
        scene.style = "stock_broll"
        updated = sb.model_copy(deep=False)
        updated.version = (sb.version or 1) + 1
        storyboard_store.save(db, updated)
        db.add(Event(
            id=str(uuid.uuid4()),
            job_id=job_id,
            event_type="BROLL_SEARCHED",
            payload={"scene_index": scene_index, "query": query, "results": len(candidates)},
        ))
        db.commit()

    return {
        "scene_index": scene_index,
        "query": query,
        "candidates": [c.model_dump() for c in candidates],
        "storyboard": sb.model_dump(mode="json"),
    }


@router.patch("/{job_id}/scenes/{scene_index}/broll")
def patch_scene_broll(
    job_id: str,
    scene_index: int,
    payload: SceneStylePatchRequest,
    db: Session = Depends(get_db),
):
    """Select a B-roll candidate or toggle a scene's style (whiteboard ↔ stock_broll)."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    sb = storyboard_store.get_by_job(db, job_id)
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    if scene_index < 0 or scene_index >= len(sb.scenes):
        raise HTTPException(status_code=404, detail="Scene index out of range")

    scene = sb.scenes[scene_index]
    changed = False
    if payload.style is not None:
        scene.style = payload.style
        changed = True
    if payload.selected_idx is not None:
        scene.selected_media_idx = payload.selected_idx
        changed = True

    if changed:
        sb.version = (sb.version or 1) + 1
        storyboard_store.save(db, sb)
        db.commit()

    return {"ok": True, "storyboard": sb.model_dump(mode="json")}


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


@router.get("/{job_id}/storyboard")
def get_storyboard(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    sb = storyboard_store.get_by_job(db, job_id)
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not yet generated")
    return sb.model_dump(mode="json")


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
