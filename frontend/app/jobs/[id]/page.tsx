"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft, Check, Download, Loader2, RefreshCw,
  RotateCcw, Save, Sparkles, Wand2, Zap,
} from "lucide-react";

import {
  assetUrl,
  editStoryboard,
  getJob,
  getStoryboard,
  getSegment,
  jobStreamUrl,
  patchSceneBroll,
  regenerateSegment,
  renderJob,
  searchBroll,
  updateSegment,
  type JobStatusResponse,
  type MediaCandidate,
} from "@/lib/api";
import { cx, prettyJson } from "@/lib/utils";

function assetsForSegment(job: JobStatusResponse | null, segmentId: string) {
  const out: Record<string, any[]> = {};
  for (const [t, arr] of Object.entries(job?.artifacts || {})) {
    out[t] = (arr as any[]).filter((a) => String(a.segment_id || "") === segmentId);
  }
  return out;
}

const STATUS_DOT: Record<string, string> = {
  SUCCEEDED: "bg-emerald-400",
  FAILED: "bg-red-400",
  RUNNING: "bg-violet-400 animate-pulse",
  QUEUED: "bg-zinc-600",
  PLANNED: "bg-amber-400",
  PLANNING: "bg-amber-400 animate-pulse",
};

const STATUS_BADGE: Record<string, string> = {
  SUCCEEDED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  FAILED: "text-red-400 bg-red-500/10 border-red-500/20",
  RUNNING: "text-violet-400 bg-violet-500/10 border-violet-500/20",
  QUEUED: "text-zinc-400 bg-white/5 border-white/10",
  PLANNED: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  PLANNING: "text-amber-400 bg-amber-500/10 border-amber-500/20",
};

export default function StudioPage() {
  const params = useParams();
  const jobId = String(params.id || "");

  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [selectedSegId, setSelectedSegId] = useState<string | null>(null);
  const [segDetail, setSegDetail] = useState<any | null>(null);
  const [scriptText, setScriptText] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [regenBusy, setRegenBusy] = useState(false);
  const [renderBusy, setRenderBusy] = useState(false);
  const [magicText, setMagicText] = useState("");
  const [magicBusy, setMagicBusy] = useState(false);
  const [magicMsg, setMagicMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // B-roll state — keyed by segment_index so switching scenes works correctly
  const [brollCandidates, setBrollCandidates] = useState<MediaCandidate[]>([]);
  const [brollBusy, setBrollBusy] = useState(false);
  const [storyboard, setStoryboard] = useState<Record<string, any> | null>(null);

  async function load() {
    try {
      const j = await getJob(jobId);
      setJob(j);
      setErr(null);
      const segs = (j.segments || []) as any[];
      if (!selectedSegId && segs.length) setSelectedSegId(segs[0].id);
    } catch (e: any) {
      setErr(e?.message || "Failed to load job");
    }
  }

  useEffect(() => {
    if (!jobId) return;
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    let es: EventSource | null = null;
    try { es = new EventSource(jobStreamUrl(jobId)); } catch { return; }
    const types = [
      "SEGMENT_STARTED", "SEGMENT_SCRIPT_DONE", "SEGMENT_TTS_DONE",
      "SEGMENT_SCENE_READY", "SEGMENT_VIDEO_DONE", "SEGMENT_COMPLETE",
      "SEGMENT_FAILED", "REGEN_STARTED", "JOB_COMPLETE",
    ];
    for (const t of types) es.addEventListener(t, () => load());
    return () => { try { es?.close(); } catch {} };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  useEffect(() => {
    (async () => {
      if (!jobId || !selectedSegId) return;
      try {
        const d = await getSegment(jobId, selectedSegId);
        setSegDetail(d);
        setScriptText(String(d.script_override ?? d.script ?? ""));
        setSaveMsg("");
      } catch {}
    })();
  }, [jobId, selectedSegId]);

  const segs = useMemo(
    () => ((job?.segments as any[]) || []).sort((a, b) => a.segment_index - b.segment_index),
    [job],
  );

  const finalVideo = useMemo(() => {
    const vids = (job?.artifacts?.video || []) as any[];
    return vids.find((a) => a?.meta?.kind === "final_mp4") || vids[0] || null;
  }, [job]);

  const selectedSeg = useMemo(() => segs.find((s) => s.id === selectedSegId), [segs, selectedSegId]);

  const segAssets = useMemo(() => {
    if (!selectedSegId) return {} as Record<string, any[]>;
    return assetsForSegment(job, selectedSegId);
  }, [job, selectedSegId]);

  const segVideo = useMemo(() => {
    const vids = (segAssets.video || []) as any[];
    return vids.find((a) => a?.meta?.kind === "scene_mp4") || vids[0] || null;
  }, [segAssets]);

  const segThumb = useMemo(() => {
    const imgs = (segAssets.image || []) as any[];
    return imgs.find((a) => a?.meta?.kind === "segment_thumbnail") || imgs[0] || null;
  }, [segAssets]);

  async function onSave() {
    if (!jobId || !selectedSegId) return;
    let sg: any = null;
    try { sg = JSON.parse(segDetail?.scenegraph_override ? prettyJson(segDetail.scenegraph_override) : "{}"); } catch {}
    await updateSegment(jobId, selectedSegId, { script_override: scriptText, scenegraph_override: sg });
    setSaveMsg("Saved");
    setTimeout(() => setSaveMsg(""), 1500);
  }

  async function onClear() {
    if (!jobId || !selectedSegId) return;
    await updateSegment(jobId, selectedSegId, { script_override: "", scenegraph_override: {} });
    const d = await getSegment(jobId, selectedSegId);
    setSegDetail(d);
    setScriptText(String(d.script ?? ""));
    setSaveMsg("Cleared");
    setTimeout(() => setSaveMsg(""), 1500);
  }

  // Clear B-roll candidates when selected scene changes
  useEffect(() => {
    const scene = storyboard?.scenes?.[selectedSeg ? segs.findIndex((s) => s.id === selectedSegId) : -1];
    setBrollCandidates(scene?.media_candidates ?? []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSegId, storyboard]);

  async function onFindBroll() {
    if (!jobId || !selectedSegId) return;
    const sceneIdx = segs.findIndex((s) => s.id === selectedSegId);
    if (sceneIdx < 0) return;
    setBrollBusy(true);
    try {
      const res = await searchBroll(jobId, sceneIdx, selectedSeg?.title ?? undefined);
      setStoryboard(res.storyboard);
      setBrollCandidates(res.candidates);
    } catch { /* ignore */ }
    finally { setBrollBusy(false); }
  }

  async function onSelectBroll(idx: number) {
    if (!jobId || !selectedSegId) return;
    const sceneIdx = segs.findIndex((s) => s.id === selectedSegId);
    if (sceneIdx < 0) return;
    const res = await patchSceneBroll(jobId, sceneIdx, { selected_idx: idx });
    setStoryboard(res.storyboard);
  }

  async function onToggleStyle(style: "whiteboard" | "stock_broll") {
    if (!jobId || !selectedSegId) return;
    const sceneIdx = segs.findIndex((s) => s.id === selectedSegId);
    if (sceneIdx < 0) return;
    const res = await patchSceneBroll(jobId, sceneIdx, { style });
    setStoryboard(res.storyboard);
  }

  async function onMagicEdit() {
    const text = magicText.trim();
    if (!text || !jobId) return;
    setMagicBusy(true);
    setMagicMsg(null);
    try {
      const result = await editStoryboard(jobId, text);
      const n = result.changes?.length ?? 0;
      setMagicMsg({ ok: true, text: n > 0 ? `${n} change${n !== 1 ? "s" : ""} applied` : "No changes needed" });
      setMagicText("");
      await load();
      if (selectedSegId) {
        const d = await getSegment(jobId, selectedSegId);
        setSegDetail(d);
        setScriptText(String(d.script_override ?? d.script ?? ""));
      }
    } catch (e: any) {
      setMagicMsg({ ok: false, text: e?.message || "Edit failed" });
    } finally {
      setMagicBusy(false);
    }
  }

  async function onRender() {
    if (!jobId) return;
    setRenderBusy(true);
    try {
      await renderJob(jobId);
      await load();
    } catch (e: any) {
      setErr(e?.message || "Failed to start render");
    } finally {
      setRenderBusy(false);
    }
  }

  async function onRegenerate() {
    if (!jobId || !selectedSegId) return;
    setRegenBusy(true);
    try {
      await regenerateSegment(jobId, selectedSegId);
      setSaveMsg("Queued…");
      setTimeout(() => setSaveMsg(""), 2000);
    } finally {
      setRegenBusy(false);
    }
  }

  const isPlanned = job?.status === "PLANNED";
  const isPlanning = job?.status === "PLANNING";
  const isGenerating = job && !["SUCCEEDED", "FAILED", "PLANNED", "PLANNING"].includes(job.status);
  const config = (job as any)?.config || {};
  const activeVideo = segVideo || finalVideo;

  return (
    <div className="flex h-[calc(100vh-57px)] overflow-hidden bg-zinc-950">

      {/* LEFT — scene strip */}
      <aside className="flex w-52 flex-shrink-0 flex-col border-r border-white/10">
        <div className="flex items-center justify-between border-b border-white/10 px-3 py-2.5">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-zinc-500 transition-colors hover:text-zinc-200"
          >
            <ArrowLeft size={12} /> New
          </Link>
          <span className="text-[11px] text-zinc-600">
            {segs.length} scene{segs.length !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {segs.map((s, i) => {
            const isActive = s.id === selectedSegId;
            const a = assetsForSegment(job, s.id);
            const thumb = ((a.image || []) as any[]).find((x) => x?.meta?.kind === "segment_thumbnail");
            return (
              <button
                key={s.id}
                onClick={() => setSelectedSegId(s.id)}
                className={cx(
                  "w-full overflow-hidden rounded-xl border text-left transition-all",
                  isActive
                    ? "border-violet-500/50 bg-violet-500/10"
                    : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.08]",
                )}
              >
                <div className="relative aspect-[9/16] w-full overflow-hidden bg-zinc-900">
                  {thumb ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={assetUrl(thumb.id)} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center">
                      {s.status === "RUNNING" || s.status === "QUEUED" ? (
                        <Loader2 size={14} className="animate-spin text-zinc-700" />
                      ) : (
                        <span className="text-sm text-zinc-800">{i + 1}</span>
                      )}
                    </div>
                  )}
                  <div className={cx(
                    "absolute right-1.5 top-1.5 h-2 w-2 rounded-full",
                    STATUS_DOT[s.status] ?? STATUS_DOT.QUEUED,
                  )} />
                </div>
                <div className="px-2 py-1.5">
                  <div className="truncate text-[11px] font-medium text-zinc-300">
                    {s.title || `Scene ${i + 1}`}
                  </div>
                  {typeof s.duration_target_sec === "number" && (
                    <div className="text-[10px] text-zinc-600">{s.duration_target_sec.toFixed(1)}s</div>
                  )}
                </div>
              </button>
            );
          })}

          {(isGenerating || isPlanning) && segs.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-12">
              <Loader2 size={18} className={cx("animate-spin", isPlanning ? "text-amber-400" : "text-violet-400")} />
              <span className="text-center text-xs text-zinc-600">
                {isPlanning ? "Planning scenes…" : "Building scenes…"}
              </span>
            </div>
          )}
        </div>

        <div className="border-t border-white/10 px-3 py-2.5">
          <span className={cx(
            "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium",
            STATUS_BADGE[job?.status ?? "QUEUED"] ?? STATUS_BADGE.QUEUED,
          )}>
            {isGenerating && <Loader2 size={9} className="animate-spin" />}
            {job?.status ?? "Loading…"}
          </span>
        </div>
      </aside>

      {/* CENTER — preview */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-600">
              {String(config.layout || "reels")} &middot; {String(config.width || 720)}×{String(config.height || 1280)}
            </span>
            <button
              onClick={load}
              className="rounded-md p-1 text-zinc-700 transition-colors hover:bg-white/5 hover:text-zinc-400"
              title="Refresh"
            >
              <RefreshCw size={12} />
            </button>
          </div>

          {finalVideo && (
            <a
              href={assetUrl(finalVideo.id)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-violet-500 px-3 py-1.5 text-xs font-semibold text-white shadow-glow transition-all hover:bg-violet-600"
            >
              <Download size={12} /> Download
            </a>
          )}
        </div>

        <div className="flex flex-1 items-center justify-center overflow-hidden p-6">
          {activeVideo ? (
            <video
              key={activeVideo.id}
              className="max-h-full max-w-full rounded-2xl shadow-soft ring-1 ring-white/10"
              src={assetUrl(activeVideo.id)}
              poster={segThumb ? assetUrl(segThumb.id) : undefined}
              controls
              playsInline
            />
          ) : isPlanning ? (
            <div className="flex flex-col items-center gap-5 text-center">
              <div className="relative flex h-20 w-20 items-center justify-center">
                <div className="absolute inset-0 animate-ping rounded-full bg-amber-500/20" />
                <div className="relative flex h-14 w-14 items-center justify-center rounded-full border border-amber-500/30 bg-amber-500/20">
                  <Sparkles size={22} className="text-amber-400" />
                </div>
              </div>
              <div>
                <div className="text-sm font-semibold text-zinc-200">Planning your storyboard…</div>
                <div className="mt-1 text-xs text-zinc-600">Generating scenes from your content</div>
              </div>
            </div>
          ) : isPlanned ? (
            <div className="flex flex-col items-center gap-6 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/10 text-violet-400">
                <Zap size={28} />
              </div>
              <div>
                <div className="text-base font-semibold text-zinc-100">Storyboard ready</div>
                <div className="mt-1 text-xs text-zinc-500">
                  {segs.length} scene{segs.length !== 1 ? "s" : ""} planned · review on the left, then render
                </div>
              </div>
              <button
                onClick={onRender}
                disabled={renderBusy}
                className={cx(
                  "inline-flex items-center gap-2 rounded-xl px-8 py-3.5 text-sm font-semibold transition-all duration-200",
                  renderBusy
                    ? "cursor-not-allowed bg-white/5 text-zinc-600"
                    : "bg-violet-500 text-white shadow-glow hover:bg-violet-600 active:scale-[0.97]",
                )}
              >
                {renderBusy ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                {renderBusy ? "Starting…" : "Render Video"}
              </button>
            </div>
          ) : isGenerating ? (
            <div className="flex flex-col items-center gap-5 text-center">
              <div className="relative flex h-20 w-20 items-center justify-center">
                <div className="absolute inset-0 animate-ping rounded-full bg-violet-500/20" />
                <div className="relative flex h-14 w-14 items-center justify-center rounded-full border border-violet-500/30 bg-violet-500/20">
                  <Zap size={22} className="text-violet-400" />
                </div>
              </div>
              <div>
                <div className="text-sm font-semibold text-zinc-200">Generating your video</div>
                <div className="mt-1 text-xs text-zinc-600">Scenes render in parallel — this takes a few minutes</div>
              </div>
              {selectedSeg && (
                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-500">
                  {selectedSeg.title || `Scene ${(selectedSeg.segment_index || 0) + 1}`} &middot; {selectedSeg.status}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/5 text-zinc-700">
                <Wand2 size={26} />
              </div>
              <div className="text-sm text-zinc-600">Select a scene to preview</div>
            </div>
          )}
        </div>

        {err && (
          <div className="border-t border-red-500/20 bg-red-500/10 px-4 py-2 text-xs text-red-400">{err}</div>
        )}
      </main>

      {/* RIGHT — edit panel */}
      <aside className="flex w-72 flex-shrink-0 flex-col border-l border-white/10">
        {/* Magic Box */}
        <div className="border-b border-white/10 p-3">
          <div className="mb-2 flex items-center gap-2">
            <Sparkles size={12} className="text-violet-400" />
            <span className="text-xs font-semibold text-zinc-300">Magic Box</span>
          </div>
          <div className="flex gap-2">
            <input
              value={magicText}
              onChange={(e) => setMagicText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !magicBusy) onMagicEdit(); }}
              placeholder='E.g. "Make scene 2 punchier"'
              disabled={magicBusy}
              className={cx(
                "flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/40",
                magicBusy ? "cursor-not-allowed text-zinc-600" : "text-zinc-300",
              )}
            />
            <button
              onClick={onMagicEdit}
              disabled={magicBusy || !magicText.trim()}
              className={cx(
                "flex items-center justify-center rounded-lg px-2.5 py-2 transition-all",
                magicBusy || !magicText.trim()
                  ? "cursor-not-allowed bg-white/5 text-zinc-700"
                  : "bg-violet-500/20 text-violet-400 hover:bg-violet-500/30",
              )}
            >
              {magicBusy
                ? <Loader2 size={12} className="animate-spin" />
                : <Sparkles size={12} />}
            </button>
          </div>
          {magicMsg && (
            <div className={cx(
              "mt-2 text-[10px]",
              magicMsg.ok ? "text-emerald-400" : "text-red-400",
            )}>
              {magicMsg.text}
            </div>
          )}
        </div>

        {/* Scene info */}
        {selectedSeg && (
          <div className="border-b border-white/10 px-3 py-2.5">
            <div className="truncate text-[11px] font-semibold text-zinc-200">
              {selectedSeg.title || `Scene ${(selectedSeg.segment_index || 0) + 1}`}
            </div>
            {selectedSeg.objective && (
              <div className="mt-0.5 line-clamp-2 text-[10px] text-zinc-600">{selectedSeg.objective}</div>
            )}
          </div>
        )}

        {/* B-roll panel — visible when a scene is selected */}
        {selectedSeg && (() => {
          const sceneIdx = segs.findIndex((s) => s.id === selectedSegId);
          const sceneData = storyboard?.scenes?.[sceneIdx];
          const currentStyle: "whiteboard" | "stock_broll" = sceneData?.style ?? "whiteboard";
          const selectedIdx: number = sceneData?.selected_media_idx ?? 0;
          return (
            <div className="border-b border-white/10 p-3 space-y-2">
              {/* Style toggle */}
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-zinc-600 mr-1">Style</span>
                {(["whiteboard", "stock_broll"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => onToggleStyle(s)}
                    className={cx(
                      "rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-all",
                      currentStyle === s
                        ? "border-violet-500/60 bg-violet-500/20 text-violet-300"
                        : "border-white/10 bg-white/5 text-zinc-500 hover:border-white/20 hover:text-zinc-300",
                    )}
                  >
                    {s === "whiteboard" ? "Whiteboard" : "B-roll"}
                  </button>
                ))}
              </div>

              {/* B-roll candidates grid */}
              {currentStyle === "stock_broll" && (
                <>
                  {brollCandidates.length > 0 ? (
                    <div className="grid grid-cols-3 gap-1">
                      {brollCandidates.map((c, i) => (
                        <button
                          key={i}
                          onClick={() => onSelectBroll(i)}
                          className={cx(
                            "relative aspect-[9/16] w-full overflow-hidden rounded-lg border transition-all",
                            i === selectedIdx
                              ? "border-violet-500/70"
                              : "border-white/10 hover:border-white/30",
                          )}
                        >
                          {c.thumb_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={c.thumb_url} alt="" className="h-full w-full object-cover" />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center bg-zinc-900 text-[9px] text-zinc-600">
                              {c.source}
                            </div>
                          )}
                          {i === selectedIdx && (
                            <div className="absolute inset-0 flex items-center justify-center bg-violet-500/20">
                              <Check size={12} className="text-violet-300" />
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[10px] text-zinc-600">No candidates yet — click Find B-roll</p>
                  )}
                  <button
                    onClick={onFindBroll}
                    disabled={brollBusy}
                    className={cx(
                      "flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/10 py-1.5 text-[10px] font-medium transition-all",
                      brollBusy
                        ? "cursor-not-allowed text-zinc-700"
                        : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-zinc-200",
                    )}
                  >
                    {brollBusy ? <Loader2 size={10} className="animate-spin" /> : <RefreshCw size={10} />}
                    {brollCandidates.length ? "Shuffle" : "Find B-roll"}
                  </button>
                </>
              )}
            </div>
          );
        })()}

        {/* Script editor */}
        <div className="flex flex-1 flex-col overflow-hidden p-3">
          <div className="mb-1.5 text-[11px] font-semibold text-zinc-500">Script</div>
          <textarea
            value={scriptText}
            onChange={(e) => setScriptText(e.target.value)}
            className="flex-1 resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-xs text-zinc-300 placeholder-zinc-700 outline-none transition-colors focus:border-violet-500/40 focus:bg-white/[0.08]"
            placeholder="Edit narration script…"
          />
        </div>

        {/* Actions */}
        <div className="border-t border-white/10 p-3 space-y-2">
          {saveMsg && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <Check size={11} /> {saveMsg}
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={onSave}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 py-2 text-xs text-zinc-300 transition-all hover:bg-white/10 hover:text-white"
            >
              <Save size={12} /> Save
            </button>
            <button
              onClick={onClear}
              title="Clear overrides"
              className="flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-zinc-500 transition-all hover:bg-white/10 hover:text-zinc-300"
            >
              <RotateCcw size={12} />
            </button>
          </div>
          <button
            onClick={onRegenerate}
            disabled={regenBusy || !selectedSegId}
            className={cx(
              "flex w-full items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-semibold transition-all",
              regenBusy || !selectedSegId
                ? "cursor-not-allowed bg-white/5 text-zinc-600"
                : "bg-violet-500 text-white shadow-glow hover:bg-violet-600 active:scale-[0.98]",
            )}
          >
            {regenBusy
              ? <Loader2 size={12} className="animate-spin" />
              : <Wand2 size={12} />}
            Regenerate Scene
          </button>
        </div>
      </aside>
    </div>
  );
}
