from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from celery import chord, group

from apps.api.settings import settings
from apps.worker.celery_app import celery_app
from core.agents.supervisor import plan_storyboard
from core.storyboard import store as storyboard_store
from core.agents.teacher import teach
from core.agents.scenegraph import plan_scenegraph
from core.ingestion.chunking import chunk_text
from core.ingestion.pdf_extract import ingest_pdf
from core.tts.base import TTSConfig
from core.tts.router import synthesize_with_fallback
from core.video.assemble import write_srt
from core.video.whiteboard_concat import concat_mp4_clips
from core.whiteboard.render import render_html_to_mp4
from core.whiteboard.storyboard import bullets_from_script, estimate_duration_sec
from core.whiteboard.scenegraph_renderer import render_scene_html

from db.models import Asset, Document, Job, Segment
from ._db import db_session, emit_event, set_job_status


def _job_dir(job_id: str) -> str:
    p = os.path.join(settings.data_dir, "outputs", job_id)
    os.makedirs(p, exist_ok=True)
    return p


def _doc_path(document_id: str) -> str:
    """Return an existing upload path (.pdf preferred, else .txt)."""
    up = os.path.join(settings.data_dir, "uploads")
    pdf = os.path.join(up, f"{document_id}.pdf")
    if os.path.exists(pdf):
        return pdf
    txt = os.path.join(up, f"{document_id}.txt")
    if os.path.exists(txt):
        return txt
    return pdf  # default for error messages


def _doc_extract_dir(document_id: str) -> str:
    p = os.path.join(settings.data_dir, "extracted", document_id)
    os.makedirs(p, exist_ok=True)
    return p


def _write_json(path: str, obj: Any) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return path


def _write_text(path: str, text: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text or "", encoding="utf-8")
    return path


def _ffprobe_duration(path: str) -> Optional[float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        out = subprocess.check_output(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore").strip()
        return float(out) if out else None
    except Exception:
        return None


def _add_asset(
    db,
    *,
    job_id: str,
    type_: str,
    uri: str,
    segment_id: str | None = None,
    meta: dict | None = None,
):
    a = Asset(id=str(uuid.uuid4()), job_id=job_id, segment_id=segment_id, type=type_, uri=uri, meta=meta or {})
    db.add(a)
    return a


def _load_outline(out_dir: str) -> dict:
    p = Path(out_dir) / "outline.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _select_chunks(chunks: List[Dict[str, Any]], *, title: str, key_phrases: List[str], k: int = 6) -> List[Dict[str, Any]]:
    """Cheap relevance scoring for MVP (offline, deterministic)."""
    if not chunks:
        return []

    title_terms = [t.lower() for t in title.split() if len(t) >= 4]
    key_terms = [t.lower() for t in (key_phrases or []) if len(t) >= 4][:18]

    def score(c: Dict[str, Any]) -> int:
        txt = (c.get("text") or "").lower()
        s = 0
        for t in title_terms:
            s += txt.count(t)
        for t in key_terms:
            s += 2 * txt.count(t)
        return s

    ranked = sorted(chunks, key=score, reverse=True)
    top = ranked[: max(1, k)]
    # If scoring is empty (common on prompt-only input), just take first chunks.
    if score(top[0]) == 0:
        return chunks[: max(1, k)]
    return top


@celery_app.task(name="apps.worker.tasks.pipeline.run_job")
def run_job(job_id: str):
    """Orchestrate rendering. If a storyboard already exists (plan-first flow), skip
    ingest/chunk/plan and jump straight to the render chord."""
    db = db_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            return

        mode = (job.mode or "quick").lower()

        set_job_status(db, job_id, "RUNNING", progress={"stage": "START"})
        emit_event(db, job_id, "JOB_STARTED", {"mode": mode})
        db.commit()

        # ── Fast path: storyboard was already created by the API route ──────────
        existing_sb = storyboard_store.get_by_job(db, job_id)
        if existing_sb:
            segs = db.execute(
                select(Segment)
                .where(Segment.job_id == job_id)
                .order_by(Segment.segment_index.asc())
            ).scalars().all()

            if not segs:
                raise RuntimeError("Plan-first job has no segments")

            out_dir = _job_dir(job_id)
            outline = {
                "title": existing_sb.title,
                "storyboard_id": existing_sb.storyboard_id,
                "scenes": [{"title": s.title, "objective": s.objective} for s in existing_sb.scenes],
            }
            outline_path = _write_json(os.path.join(out_dir, "outline.json"), outline)
            _add_asset(db, job_id=job_id, type_="json", uri=outline_path, meta={"kind": "outline"})

            # Write minimal source text for render_segment chunk lookup
            doc = db.get(Document, job.document_id)
            in_path = _doc_path(job.document_id)
            if os.path.exists(in_path) and not (Path(out_dir) / "chunks.json").exists():
                text = ""
                if in_path.lower().endswith(".pdf"):
                    extract_dir = _doc_extract_dir(job.document_id)
                    try:
                        manifest = ingest_pdf(in_path, extract_dir, max_pages=8, max_images=12)
                        tp = manifest.get("text_path")
                        if tp and Path(tp).exists():
                            text = Path(tp).read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        pass
                else:
                    text = Path(in_path).read_text(encoding="utf-8", errors="ignore")
                if text.strip():
                    _write_text(os.path.join(out_dir, "source.txt"), text)
                    chunks = chunk_text(text, max_chars=2500)
                    _write_json(os.path.join(out_dir, "chunks.json"), chunks)

            segment_ids = [s.id for s in segs]
            set_job_status(db, job_id, "RUNNING", progress={"stage": "RENDER_DISPATCH"})
            emit_event(db, job_id, "RENDER_DISPATCH", {"segments": len(segment_ids)})
            db.commit()

            header = group(render_segment.s(job_id, sid) for sid in segment_ids)
            chord(header)(assemble_job.s(job_id))
            return

        # ── Slow path: full ingest → chunk → plan → render (legacy / fallback) ──
        doc = db.get(Document, job.document_id)
        if not doc:
            set_job_status(db, job_id, "FAILED", progress={"error": "Document missing"})
            emit_event(db, job_id, "FAILED", {"error": "Document missing"})
            db.commit()
            return

        in_path = _doc_path(job.document_id)
        if not os.path.exists(in_path):
            set_job_status(db, job_id, "FAILED", progress={"error": "Input not found"})
            emit_event(db, job_id, "FAILED", {"error": f"Input not found: {in_path}"})
            db.commit()
            return

        out_dir = _job_dir(job_id)
        _write_text(os.path.join(out_dir, "job_meta.txt"), f"job_id={job_id}\nmode={mode}\ndoc={doc.filename}\n")

        set_job_status(db, job_id, "RUNNING", progress={"stage": "INGEST"})
        emit_event(db, job_id, "INGESTION_STARTED", {"input": Path(in_path).suffix.lower()})
        db.commit()

        text = ""
        if in_path.lower().endswith(".pdf"):
            extract_dir = _doc_extract_dir(job.document_id)
            manifest = ingest_pdf(in_path, extract_dir, max_pages=8, max_images=12)
            text_path = manifest.get("text_path")
            if text_path and Path(text_path).exists():
                text = Path(text_path).read_text(encoding="utf-8", errors="ignore")
        else:
            text = Path(in_path).read_text(encoding="utf-8", errors="ignore")

        if not text.strip():
            text = "(No extractable text found.)"

        _write_text(os.path.join(out_dir, "source.txt"), text)
        emit_event(db, job_id, "INGESTION_COMPLETE", {"chars": len(text)})
        db.commit()

        set_job_status(db, job_id, "RUNNING", progress={"stage": "CHUNK"})
        chunks = chunk_text(text, max_chars=2500)
        _write_json(os.path.join(out_dir, "chunks.json"), chunks)
        emit_event(db, job_id, "CHUNKING_COMPLETE", {"chunks": len(chunks)})
        db.commit()

        set_job_status(db, job_id, "RUNNING", progress={"stage": "PLAN"})
        cfg = getattr(job, "config", None) or {}
        aspect_ratio = str(cfg.get("aspect_ratio") or cfg.get("layout") or "9:16")
        aspect_ratio = {"reels": "9:16", "landscape": "16:9", "square": "1:1"}.get(aspect_ratio, aspect_ratio)
        length_preset = str(cfg.get("length_preset") or ("30s" if mode == "quick" else "3m"))

        storyboard = plan_storyboard(
            text=text,
            job_id=job_id,
            title=(doc.filename or "").rsplit(".", 1)[0] or "",
            aspect_ratio=aspect_ratio,
            length_preset=length_preset,
            mode=mode,
        )
        storyboard_store.save(db, storyboard)

        outline = {
            "title": storyboard.title,
            "storyboard_id": storyboard.storyboard_id,
            "scenes": [{"title": s.title, "objective": s.objective} for s in storyboard.scenes],
        }
        outline_path = _write_json(os.path.join(out_dir, "outline.json"), outline)
        _add_asset(db, job_id=job_id, type_="json", uri=outline_path, meta={"kind": "outline"})
        emit_event(db, job_id, "PLAN_COMPLETE", {"scenes": len(storyboard.scenes), "storyboard_id": storyboard.storyboard_id})
        db.commit()

        scenes = storyboard.scenes
        if not scenes:
            from core.storyboard.schema import Scene as SBScene
            scenes = [SBScene(title="Overview", objective="Cover the topic", script="")]

        segment_ids: List[str] = []
        for scene in scenes:
            seg_id = str(uuid.uuid4())
            segment_ids.append(seg_id)
            db.add(Segment(
                id=seg_id,
                job_id=job_id,
                segment_index=scene.order,
                title=scene.title,
                objective=scene.objective,
                script="",
                script_override=scene.script,
                citations=[],
                key_terms=[],
                status="QUEUED",
                duration_target_sec=float(scene.duration_s),
            ))

        set_job_status(db, job_id, "RUNNING", progress={"stage": "RENDER_DISPATCH"})
        emit_event(db, job_id, "RENDER_DISPATCH", {"segments": len(segment_ids)})
        db.commit()

        header = group(render_segment.s(job_id, seg_id) for seg_id in segment_ids)
        chord(header)(assemble_job.s(job_id))

    except Exception as e:
        try:
            set_job_status(db, job_id, "FAILED", progress={"error": str(e), "stage": "FAILED"})
            emit_event(db, job_id, "FAILED", {"error": str(e)})
            db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


@celery_app.task(name="apps.worker.tasks.pipeline.render_segment")
def render_segment(job_id: str, segment_id: str) -> str:
    """Render one whiteboard scene (SVG -> Playwright video) + TTS."""
    db = db_session()
    try:
        seg = db.get(Segment, segment_id)
        job = db.get(Job, job_id)
        doc = db.get(Document, job.document_id) if job else None
        if not seg or not job:
            return segment_id

        out_dir = _job_dir(job_id)
        seg.status = "RUNNING"
        db.add(seg)
        emit_event(db, job_id, "SEGMENT_STARTED", {"segment_id": segment_id, "index": seg.segment_index})
        db.commit()

        # Load chunks and outline
        chunks_path = Path(out_dir) / "chunks.json"
        chunks = json.loads(chunks_path.read_text(encoding="utf-8")) if chunks_path.exists() else []
        outline = _load_outline(out_dir)
        key_phrases = outline.get("key_phrases", []) if isinstance(outline, dict) else []

        chosen_chunks = _select_chunks(chunks, title=seg.title or "", key_phrases=key_phrases, k=6)

        # Allow UI overrides ("click on text to edit")
        script_override = (getattr(seg, "script_override", "") or "").strip()
        if script_override:
            script = script_override
            citations = getattr(seg, "citations", None) or []
            key_terms = getattr(seg, "key_terms", None) or []
            emit_event(db, job_id, "SEGMENT_SCRIPT_OVERRIDE", {"segment_id": segment_id})
        else:
            teach_out = teach(
                segment_title=seg.title or f"Part {seg.segment_index+1}",
                objective=seg.objective or "",
                chunks=chosen_chunks,
                depth=getattr(job, "mode", "quick") or "quick",
            )
            script = (teach_out.get("script") or "").strip()
            citations = teach_out.get("citations") or []
            key_terms = teach_out.get("key_terms") or []

        seg.script = script
        seg.citations = citations
        seg.key_terms = key_terms
        db.add(seg)
        emit_event(db, job_id, "SEGMENT_SCRIPT_DONE", {"segment_id": segment_id, "index": seg.segment_index})
        db.commit()

        # Write segment artifacts
        seg_dir = Path(out_dir) / "segments" / f"{seg.segment_index:02d}_{segment_id[:8]}"
        seg_dir.mkdir(parents=True, exist_ok=True)
        script_path = _write_text(str(seg_dir / "script.txt"), script)
        _add_asset(db, job_id=job_id, segment_id=segment_id, type_="text", uri=script_path, meta={"kind": "segment_script"})

        # TTS
        audio_path = str(seg_dir / "narration.mp3")
        tts_cfg = TTSConfig(voice="en-us", rate=170, volume=100)
        audio_path, provider_name = synthesize_with_fallback(script, audio_path, cfg=tts_cfg)
        _add_asset(db, job_id=job_id, segment_id=segment_id, type_="audio", uri=audio_path, meta={"kind": "segment_audio", "provider": provider_name})

        emit_event(db, job_id, "SEGMENT_TTS_DONE", {"segment_id": segment_id, "index": seg.segment_index, "provider": provider_name})

        dur = _ffprobe_duration(audio_path) or estimate_duration_sec(script)
        seg.duration_target_sec = float(dur)
        db.add(seg)
        db.commit()

        cfg = getattr(job, "config", None) or {}
        width = int(cfg.get("width") or 1280)
        height = int(cfg.get("height") or 720)
        video_style = str(cfg.get("video_style") or "education")

        # ── B-roll path: download stock clip instead of Playwright render ────────
        sb = storyboard_store.get_by_job(db, job_id)
        scene_obj = None
        if sb and 0 <= seg.segment_index < len(sb.scenes):
            scene_obj = sb.scenes[seg.segment_index]

        mp4_path = str(seg_dir / "scene.mp4")

        if scene_obj and scene_obj.style == "stock_broll" and scene_obj.media_candidates:
            idx = min(scene_obj.selected_media_idx, len(scene_obj.media_candidates) - 1)
            candidate = scene_obj.media_candidates[idx]
            if candidate.url:
                from core.broll.download import download_clip, fit_clip_to_frame
                emit_event(db, job_id, "SEGMENT_BROLL_DOWNLOAD", {"segment_id": segment_id, "source": candidate.source})
                raw_path = str(seg_dir / "broll_raw.mp4")
                download_clip(candidate.url, raw_path, timeout_sec=90.0)
                fit_clip_to_frame(raw_path, mp4_path, width, height, float(dur), audio_path)
                _add_asset(db, job_id=job_id, segment_id=segment_id, type_="video", uri=mp4_path, meta={"kind": "scene_mp4", "duration_sec": float(dur), "width": width, "height": height, "broll_source": candidate.source})
                emit_event(db, job_id, "SEGMENT_VIDEO_DONE", {"segment_id": segment_id, "index": seg.segment_index, "duration_sec": float(dur)})
            else:
                # Candidate has no URL — fall through to whiteboard render
                scene_obj = None

        # ── Whiteboard path: SceneGraph → Playwright ──────────────────────────────
        if not (scene_obj and scene_obj.style == "stock_broll" and os.path.exists(mp4_path)):
            sg_override = getattr(seg, "scenegraph_override", None) or {}
            if isinstance(sg_override, dict) and sg_override:
                scenegraph = sg_override
                emit_event(db, job_id, "SEGMENT_SCENEGRAPH_OVERRIDE", {"segment_id": segment_id})
            else:
                scenegraph = plan_scenegraph(
                    title=seg.title or f"Part {seg.segment_index+1}",
                    objective=seg.objective or "",
                    script=script,
                    video_style=video_style,
                    width=width,
                    height=height,
                    mode=getattr(job, "mode", "quick") or "quick",
                )

            seg.scenegraph = scenegraph
            db.add(seg)
            db.commit()

            sg_path = _write_json(str(seg_dir / "scenegraph.json"), scenegraph)
            _add_asset(db, job_id=job_id, segment_id=segment_id, type_="json", uri=sg_path, meta={"kind": "scenegraph"})

            html_str, html_meta = render_scene_html(scenegraph, width=width, height=height, video_style=video_style)
            html_path = _write_text(str(seg_dir / "scene.html"), html_str)
            _add_asset(db, job_id=job_id, segment_id=segment_id, type_="html", uri=html_path, meta={"kind": "scene_html", **(html_meta or {})})
            emit_event(db, job_id, "SEGMENT_SCENE_READY", {"segment_id": segment_id, "index": seg.segment_index})

            render_html_to_mp4(html_path, mp4_path, duration_sec=float(dur), audio_path=audio_path, width=width, height=height)
            _add_asset(db, job_id=job_id, segment_id=segment_id, type_="video", uri=mp4_path, meta={"kind": "scene_mp4", "duration_sec": float(dur), "width": width, "height": height})
            emit_event(db, job_id, "SEGMENT_VIDEO_DONE", {"segment_id": segment_id, "index": seg.segment_index, "duration_sec": float(dur)})

        # Thumbnail for Studio sidebar
        thumb_path = str(seg_dir / "thumb.jpg")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", mp4_path, "-vf", "thumbnail,scale=240:-1", "-frames:v", "1", thumb_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            _add_asset(db, job_id=job_id, segment_id=segment_id, type_="image", uri=thumb_path, meta={"kind": "segment_thumbnail"})
        except Exception:
            pass

        seg.status = "SUCCEEDED"
        db.add(seg)
        emit_event(db, job_id, "SEGMENT_COMPLETE", {"segment_id": segment_id, "index": seg.segment_index, "duration_sec": float(dur)})
        db.commit()
        return segment_id
    except Exception as e:
        try:
            seg = db.get(Segment, segment_id)
            if seg:
                seg.status = "FAILED"
                db.add(seg)
            idx = getattr(seg, "segment_index", None) if seg else None
            emit_event(db, job_id, "SEGMENT_FAILED", {"segment_id": segment_id, "index": idx, "error": str(e)})
            db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


@celery_app.task(name="apps.worker.tasks.pipeline.assemble_job")
def assemble_job(_results: list, job_id: str) -> str:
    """Concatenate scene videos into a final MP4 and write top-level artifacts."""
    db = db_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            return job_id

        out_dir = _job_dir(job_id)
        set_job_status(db, job_id, "RUNNING", progress={"stage": "ASSEMBLE"})
        emit_event(db, job_id, "ASSEMBLE_STARTED", {})
        db.commit()

        # Collect segments ordered
        segs: List[Segment] = (
            db.query(Segment)
            .filter(Segment.job_id == job_id)
            .order_by(Segment.segment_index.asc())
            .all()
        )

        clip_paths: List[str] = []
        srt_segs: List[Dict[str, Any]] = []
        for s in segs:
            # find this segment's mp4 asset
            assets = (
                db.query(Asset)
                .filter(Asset.job_id == job_id)
                .filter(Asset.segment_id == s.id)
                .all()
            )
            mp4 = None
            for a in assets:
                if a.type == "video" and (a.meta or {}).get("kind") == "scene_mp4":
                    mp4 = a.uri
                    break
            if mp4 and os.path.exists(mp4):
                clip_paths.append(mp4)
                dur = float((a.meta or {}).get("duration_sec") or s.duration_target_sec or 12.0)
                script_text = str(getattr(s, "script_override", "") or getattr(s, "script", "") or s.title or "")
                srt_segs.append({
                    "title": s.title or f"Part {s.segment_index+1}",
                    "script": script_text,
                    "duration_sec": dur,
                    "duration_target_sec": dur,
                })

        if not clip_paths:
            raise RuntimeError("No scene clips found")

        cfg = getattr(job, "config", None) or {}
        width = int(cfg.get("width") or 1280)
        height = int(cfg.get("height") or 720)
        layout = str(cfg.get("layout") or "laptop")
        video_style = str(cfg.get("video_style") or "education")

        final_dir = Path(out_dir) / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        # V1.5 naming convention
        final_mp4 = str(final_dir / f"final_{layout}_{width}x{height}.mp4")
        concat_mp4_clips(clip_paths, final_mp4)

        # Captions — build proper SRT from scripts and optionally burn in
        caption_style = str(cfg.get("caption_style") or "minimal")
        from core.video.captions import build_job_srt, burn_captions as _burn_captions

        script_srt_path = str(final_dir / "captions_script.srt")
        build_job_srt(srt_segs, script_srt_path)

        # Legacy title-only SRT kept for downstream use
        srt_path = str(final_dir / "captions.srt")
        write_srt(srt_segs, srt_path)

        if caption_style != "off" and shutil.which("ffmpeg"):
            captioned_path = str(final_dir / "captioned_tmp.mp4")
            try:
                _burn_captions(final_mp4, script_srt_path, captioned_path, style=caption_style)
                Path(captioned_path).replace(Path(final_mp4))
                emit_event(db, job_id, "CAPTIONS_BURNED", {"style": caption_style})
            except Exception as cap_err:
                emit_event(db, job_id, "CAPTIONS_FAILED", {"style": caption_style, "error": str(cap_err)})

        # Thumbnail
        ffmpeg = shutil.which("ffmpeg")
        thumb_path = str(final_dir / "thumbnail.jpg")
        if ffmpeg:
            subprocess.run(
                [ffmpeg, "-y", "-i", final_mp4, "-vf", "thumbnail,scale=640:-1", "-frames:v", "1", "-q:v", "3", thumb_path],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Persist assets
        _add_asset(db, job_id=job_id, type_="video", uri=final_mp4, meta={"kind": "final_mp4", "layout": layout, "width": width, "height": height, "video_style": video_style, "caption_style": caption_style})
        _add_asset(db, job_id=job_id, type_="caption", uri=srt_path, meta={"kind": "srt"})
        if os.path.exists(thumb_path):
            _add_asset(db, job_id=job_id, type_="image", uri=thumb_path, meta={"kind": "thumbnail"})

        # video meta
        dur = _ffprobe_duration(final_mp4) or sum(float(x["duration_target_sec"]) for x in srt_segs)
        _add_asset(db, job_id=job_id, type_="json", uri=_write_json(str(final_dir / "video_meta.json"), {"duration_sec": dur}), meta={"kind": "video_meta", "duration_sec": dur})

        set_job_status(db, job_id, "SUCCEEDED", progress={"stage": "DONE"})
        emit_event(db, job_id, "JOB_COMPLETE", {"duration_sec": dur})
        db.commit()
        return job_id

    except Exception as e:
        set_job_status(db, job_id, "FAILED", progress={"stage": "FAILED", "error": str(e)})
        emit_event(db, job_id, "FAILED", {"error": str(e)})
        db.commit()
        raise
    finally:
        db.close()

@celery_app.task(name="apps.worker.tasks.pipeline.regenerate_segment")
def regenerate_segment(job_id: str, segment_id: str) -> str:
    """Selective Scene Regeneration.

    Renders ONLY the chosen segment (script->TTS->scene render) and then
    re-stitches the final video using the existing per-segment MP4s.

    This avoids re-rendering the entire job while keeping A/V sync: each
    segment MP4 is muxed with its own narration, and the final concat uses
    the updated segment durations to regenerate the SRT.
    """
    db = db_session()
    try:
        job = db.get(Job, job_id)
        seg = db.get(Segment, segment_id)
        if not job or not seg or seg.job_id != job_id:
            return job_id

        set_job_status(db, job_id, "RUNNING", progress={"stage": "REGENERATE", "segment_id": segment_id})
        emit_event(db, job_id, "REGEN_STARTED", {"segment_id": segment_id})
        db.commit()
    finally:
        db.close()

    # Render the segment (do the heavy work outside the shared DB session)
    render_segment(job_id, segment_id)

    # Re-stitch final output
    assemble_job([], job_id)
    return job_id
