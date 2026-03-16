"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Download, RefreshCw, RotateCcw, Save, Wand2 } from "lucide-react";

import { Stepper } from "@/components/Stepper";
import {
  assetUrl,
  getJob,
  getSegment,
  regenerateSegment,
  updateSegment,
  jobStreamUrl,
  type JobStatusResponse,
} from "@/lib/api";
import { cx, prettyJson } from "@/lib/utils";

const STEPS = [
  { key: "upload", label: "Upload Document" },
  { key: "options", label: "Set Options" },
  { key: "preview", label: "Preview" },
];

function findByKind(job: JobStatusResponse | null, type: string, kind?: string) {
  const list = (job?.artifacts?.[type] || []) as any[];
  if (!kind) return list[0] || null;
  return list.find((a) => String(a?.meta?.kind) === kind) || null;
}

function assetsForSegment(job: JobStatusResponse | null, segmentId: string) {
  const out: Record<string, any[]> = {};
  const artifacts = job?.artifacts || {};
  for (const [t, arr] of Object.entries(artifacts)) {
    out[t] = (arr as any[]).filter((a) => String(a.segment_id || "") === segmentId);
  }
  return out;
}

export default function StudioPage() {
  const params = useParams();
  const jobId = String(params.id || "");

  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const [selectedSegId, setSelectedSegId] = useState<string | null>(null);
  const [segDetail, setSegDetail] = useState<any | null>(null);

  const [tab, setTab] = useState<"script" | "scenegraph">("script");
  const [scriptText, setScriptText] = useState<string>("");
  const [scenegraphText, setScenegraphText] = useState<string>("");
  const [saveMsg, setSaveMsg] = useState<string>("");
  const [regenBusy, setRegenBusy] = useState(false);

  const segmentVideoRef = useRef<HTMLVideoElement | null>(null);

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

  // Live SSE updates (segment status + regen notifications)
  useEffect(() => {
    if (!jobId) return;
    let es: EventSource | null = null;
    try {
      es = new EventSource(jobStreamUrl(jobId));
    } catch {
      return;
    }
    const onAny = () => {
      // lightweight refresh; job status endpoint is cached in memory anyway
      load();
    };
    const types = [
      "SEGMENT_STARTED",
      "SEGMENT_SCRIPT_DONE",
      "SEGMENT_TTS_DONE",
      "SEGMENT_SCENE_READY",
      "SEGMENT_VIDEO_DONE",
      "SEGMENT_COMPLETE",
      "SEGMENT_FAILED",
      "REGEN_STARTED",
      "JOB_COMPLETE",
    ];
    for (const t of types) es.addEventListener(t, onAny);
    return () => {
      try {
        es?.close();
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  // Load selected segment details (script + scenegraph)
  useEffect(() => {
    (async () => {
      if (!jobId || !selectedSegId) return;
      try {
        const d = await getSegment(jobId, selectedSegId);
        setSegDetail(d);
        setScriptText(String(d.script_override ?? d.script ?? ""));
        setScenegraphText(prettyJson(d.scenegraph_override && Object.keys(d.scenegraph_override).length ? d.scenegraph_override : d.scenegraph || {}));
        setSaveMsg("");
      } catch {
        // ignore
      }
    })();
  }, [jobId, selectedSegId]);

  const segs = useMemo(() => ((job?.segments as any[]) || []).slice().sort((a, b) => a.segment_index - b.segment_index), [job]);

  const finalVideo = useMemo(() => {
    const vids = (job?.artifacts?.video || []) as any[];
    return vids.find((a) => a?.meta?.kind === "final_mp4") || vids[0] || null;
  }, [job]);

  const config = (job as any)?.config || {};

  const selectedSeg = useMemo(() => segs.find((s) => s.id === selectedSegId) || null, [segs, selectedSegId]);

  const segAssets = useMemo(() => {
    if (!selectedSegId) return {} as any;
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

  async function onSaveOverrides() {
    if (!jobId || !selectedSegId) return;
    setSaveMsg("");
    let scenegraphObj: any = null;
    if (tab === "scenegraph") {
      try {
        scenegraphObj = JSON.parse(scenegraphText || "{}");
      } catch {
        setSaveMsg("SceneGraph JSON is invalid.");
        return;
      }
    } else {
      // keep existing
      try {
        scenegraphObj = JSON.parse(scenegraphText || "{}");
      } catch {
        scenegraphObj = null;
      }
    }

    await updateSegment(jobId, selectedSegId, {
      script_override: scriptText,
      scenegraph_override: scenegraphObj,
    });
    setSaveMsg("Saved ✓");
    setTimeout(() => setSaveMsg(""), 1500);
  }

  async function onClearOverrides() {
    if (!jobId || !selectedSegId) return;
    await updateSegment(jobId, selectedSegId, { script_override: "", scenegraph_override: {} });
    await load();
    const d = await getSegment(jobId, selectedSegId);
    setSegDetail(d);
    setScriptText(String(d.script ?? ""));
    setScenegraphText(prettyJson(d.scenegraph || {}));
    setSaveMsg("Cleared ✓");
    setTimeout(() => setSaveMsg(""), 1500);
  }

  async function onRegenerate() {
    if (!jobId || !selectedSegId) return;
    setRegenBusy(true);
    try {
      await regenerateSegment(jobId, selectedSegId);
      setSaveMsg("Regeneration dispatched…");
      setTimeout(() => setSaveMsg(""), 2000);
    } finally {
      setRegenBusy(false);
    }
  }

  return (
    <div>
      <Stepper steps={STEPS} activeKey="preview" />

      <div className="mx-auto w-full max-w-6xl px-4 py-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="text-sm underline">
            + New
          </Link>
          <Link href="/library" className="text-sm underline">
            Library
          </Link>
          <div className="ml-2 text-sm text-neutral-600">Job</div>
          <div className="truncate font-mono text-xs text-neutral-700">{jobId}</div>
          <button
            onClick={load}
            className="ml-auto inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-sm hover:bg-neutral-50"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {err ? <div className="mt-4 text-sm text-red-700">{err}</div> : null}

        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          {/* Scenes */}
          <div className="rounded-3xl border border-neutral-200 bg-white p-4 shadow-soft">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold">Scenes</div>
              <div className="text-xs text-neutral-500">{segs.length}</div>
            </div>

            <div className="mt-3 space-y-3 max-h-[70vh] overflow-auto pr-1">
              {segs.map((s) => {
                const isActive = s.id === selectedSegId;
                const a = assetsForSegment(job, s.id);
                const thumb = ((a.image || []) as any[]).find((x) => x?.meta?.kind === "segment_thumbnail") || null;
                return (
                  <button
                    key={s.id}
                    onClick={() => setSelectedSegId(s.id)}
                    className={cx(
                      "w-full text-left rounded-2xl border p-3 hover:bg-neutral-50",
                      isActive ? "border-neutral-900 bg-neutral-50" : "border-neutral-200 bg-white"
                    )}
                  >
                    <div className="flex gap-3">
                      <div className="h-16 w-12 flex-shrink-0 overflow-hidden rounded-xl bg-neutral-100 ring-1 ring-neutral-200">
                        {thumb ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={assetUrl(thumb.id)} alt="thumb" className="h-full w-full object-cover" />
                        ) : (
                          <div className="h-full w-full" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">{s.title || `Scene ${s.segment_index + 1}`}</div>
                        <div className="mt-1 line-clamp-2 text-xs text-neutral-600">{s.objective || ""}</div>
                        <div className="mt-2 flex items-center gap-2 text-[11px]">
                          <span className={cx("rounded-full px-2 py-0.5 ring-1", s.status === "SUCCEEDED" ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : s.status === "FAILED" ? "bg-red-50 text-red-700 ring-red-200" : "bg-neutral-50 text-neutral-700 ring-neutral-200")}>
                            {s.status}
                          </span>
                          {typeof s.duration_target_sec === "number" ? <span className="text-neutral-500">{s.duration_target_sec.toFixed(1)}s</span> : null}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Preview + Editor */}
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-3xl border border-neutral-200 bg-white p-4 shadow-soft">
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-sm font-semibold">Preview</div>
                <div className="text-xs text-neutral-500">
                  {String(config.layout || "reels")} · {String(config.video_style || "education")} · {String(config.width || 720)}×{String(config.height || 1280)}
                </div>

                <div className="ml-auto flex items-center gap-2">
                  {finalVideo ? (
                    <a
                      href={assetUrl(finalVideo.id)}
                      className="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-3 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
                    >
                      <Download size={16} />
                      Download Full Video
                    </a>
                  ) : null}
                </div>
              </div>

              <div className="mt-4">
                {segVideo ? (
                  <video
                    ref={segmentVideoRef}
                    className="w-full rounded-2xl bg-black"
                    src={assetUrl(segVideo.id)}
                    poster={segThumb ? assetUrl(segThumb.id) : undefined}
                    controls
                    playsInline
                  />
                ) : finalVideo ? (
                  <video className="w-full rounded-2xl bg-black" src={assetUrl(finalVideo.id)} controls playsInline />
                ) : (
                  <div className="flex h-64 items-center justify-center rounded-2xl bg-neutral-50 text-sm text-neutral-600 ring-1 ring-neutral-200">
                    Scene is generating…
                  </div>
                )}
              </div>

              <div className="mt-4 flex items-center gap-2">
                <button
                  onClick={onSaveOverrides}
                  className="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-sm hover:bg-neutral-50"
                >
                  <Save size={16} />
                  Save
                </button>
                <button
                  onClick={onRegenerate}
                  disabled={regenBusy}
                  className={cx(
                    "inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-sm font-semibold",
                    regenBusy ? "bg-neutral-200 text-neutral-500" : "bg-neutral-900 text-white hover:bg-neutral-800"
                  )}
                >
                  <Wand2 size={16} />
                  Regenerate Scene (Option 1)
                </button>
                <button
                  onClick={onClearOverrides}
                  className="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-sm hover:bg-neutral-50"
                >
                  <RotateCcw size={16} />
                  Clear overrides
                </button>
                {saveMsg ? <div className="ml-auto text-sm text-neutral-700">{saveMsg}</div> : null}
              </div>
            </div>

            <div className="rounded-3xl border border-neutral-200 bg-white p-4 shadow-soft">
              <div className="flex items-center gap-2">
                <div className="text-sm font-semibold">Editor</div>
                <div className="text-xs text-neutral-500">Click Save → Regenerate</div>
              </div>

              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={() => setTab("script")}
                  className={cx(
                    "rounded-2xl px-3 py-2 text-sm font-semibold ring-1",
                    tab === "script" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white ring-neutral-200 hover:bg-neutral-50"
                  )}
                >
                  Script
                </button>
                <button
                  onClick={() => setTab("scenegraph")}
                  className={cx(
                    "rounded-2xl px-3 py-2 text-sm font-semibold ring-1",
                    tab === "scenegraph" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white ring-neutral-200 hover:bg-neutral-50"
                  )}
                >
                  SceneGraph
                </button>
                {segDetail?.id ? (
                  <div className="ml-auto text-xs text-neutral-500">
                    Segment: <span className="font-mono">{String(segDetail.id).slice(0, 8)}</span>
                  </div>
                ) : null}
              </div>

              {tab === "script" ? (
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  className="mt-3 h-56 w-full rounded-2xl border border-neutral-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-neutral-900"
                  placeholder="Edit narration here…"
                />
              ) : (
                <textarea
                  value={scenegraphText}
                  onChange={(e) => setScenegraphText(e.target.value)}
                  className="mt-3 h-56 w-full rounded-2xl border border-neutral-200 px-4 py-3 font-mono text-xs outline-none focus:ring-2 focus:ring-neutral-900"
                  placeholder="Edit scenegraph JSON here…"
                />
              )}

              <div className="mt-3 rounded-2xl bg-neutral-50 p-3 text-xs text-neutral-600 ring-1 ring-neutral-200">
                <div className="font-medium text-neutral-700">Notes</div>
                <div className="mt-1">
                  • Save updates overrides in the DB. • Regenerate re-renders only this scene and then re-stitches the final MP4 + captions.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
