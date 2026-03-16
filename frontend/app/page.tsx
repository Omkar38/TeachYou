"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FileUp, Sparkles } from "lucide-react";

import { Stepper } from "@/components/Stepper";
import { cx } from "@/lib/utils";
import { promptAndCreateJob, uploadAndCreateJob } from "@/lib/api";

const STEPS = [
  { key: "upload", label: "Upload Document" },
  { key: "options", label: "Set Options" },
  { key: "preview", label: "Preview" },
];

export default function CreateFlowPage() {
  const router = useRouter();
  const [step, setStep] = useState<"upload" | "options" | "preview">("upload");

  const [sourceType, setSourceType] = useState<"pdf" | "prompt">("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [promptTitle, setPromptTitle] = useState<string>("");
  const [promptText, setPromptText] = useState<string>("");

  const [mode, setMode] = useState<"quick" | "deep">("quick");
// Default per V1.5 decision (Q2: B): professional business theme (light)
  const [videoStyle, setVideoStyle] = useState<"education" | "business">("business");
  // V1.5 ships Reels-only (720×1280). Laptop is a future patch.
  const [layout] = useState<"reels">("reels");

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canContinueUpload = useMemo(() => {
    if (sourceType === "pdf") return !!file;
    return promptText.trim().length >= 40;
  }, [sourceType, file, promptText]);

  async function onContinue() {
    setErr(null);
    if (!canContinueUpload) {
      setErr(sourceType === "pdf" ? "Pick a PDF file." : "Add a bit more detail (≥ 40 characters)." );
      return;
    }
    setStep("options");
  }

  async function onGenerate() {
    setErr(null);
    setBusy(true);
    try {
      let job_id: string;
      if (sourceType === "pdf") {
        if (!file) throw new Error("Pick a PDF file");
        ({ job_id } = await uploadAndCreateJob(file, { mode, video_style: videoStyle, layout }));
      } else {
        ({ job_id } = await promptAndCreateJob(promptText, { mode, video_style: videoStyle, layout, title: promptTitle || undefined }));
      }
      setStep("preview");
      router.push(`/jobs/${job_id}`);
    } catch (e: any) {
      setErr(e?.message || "Failed to start job");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Stepper steps={STEPS} activeKey={step} />

      <div className="mx-auto w-full max-w-6xl px-4 py-8">
        <div className="flex items-center gap-3">
          <div className="text-xl font-semibold">SketchWave Studio</div>
          <div className="text-sm text-neutral-600">Document → Whiteboard Explainer (English)</div>
          <Link href="/library" className="ml-auto text-sm underline text-neutral-700">
            Library
          </Link>
        </div>

        <div className="mt-6 rounded-3xl border border-neutral-200 bg-white p-6 shadow-soft">
          {step === "upload" ? (
            <div className="space-y-6">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSourceType("pdf")}
                  className={cx(
                    "rounded-2xl px-4 py-2 text-sm font-medium ring-1",
                    sourceType === "pdf" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white text-neutral-800 ring-neutral-200 hover:bg-neutral-50"
                  )}
                >
                  PDF Upload
                </button>
                <button
                  onClick={() => setSourceType("prompt")}
                  className={cx(
                    "rounded-2xl px-4 py-2 text-sm font-medium ring-1",
                    sourceType === "prompt" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white text-neutral-800 ring-neutral-200 hover:bg-neutral-50"
                  )}
                >
                  Paste Text
                </button>
              </div>

              {sourceType === "pdf" ? (
                <div>
                  <div className="text-sm font-medium text-neutral-700">Upload a PDF</div>
                  <label className="mt-2 flex cursor-pointer items-center justify-between rounded-3xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-6 hover:bg-neutral-100">
                    <div className="flex items-center gap-3">
                      <FileUp className="h-5 w-5" />
                      <div>
                        <div className="text-sm font-semibold">Choose file</div>
                        <div className="text-xs text-neutral-600">PDF only</div>
                      </div>
                    </div>
                    <div className="text-sm text-neutral-700">{file ? file.name : "No file"}</div>
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <div className="text-sm font-medium text-neutral-700">Title (optional)</div>
                    <input
                      value={promptTitle}
                      onChange={(e) => setPromptTitle(e.target.value)}
                      className="mt-2 w-full rounded-2xl border border-neutral-200 px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-neutral-900"
                      placeholder="E.g., RAG Pipeline Basics"
                    />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-neutral-700">Text</div>
                    <textarea
                      value={promptText}
                      onChange={(e) => setPromptText(e.target.value)}
                      className="mt-2 h-40 w-full rounded-2xl border border-neutral-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-neutral-900"
                      placeholder="Paste your content here (English)."
                    />
                    <div className="mt-2 text-xs text-neutral-500">Minimum ~40 characters.</div>
                  </div>
                </div>
              )}

              {err ? <div className="text-sm text-red-700">{err}</div> : null}

              <div className="flex items-center gap-3">
                <button
                  onClick={onContinue}
                  disabled={!canContinueUpload}
                  className={cx(
                    "rounded-2xl px-4 py-2 text-sm font-semibold",
                    canContinueUpload ? "bg-neutral-900 text-white hover:bg-neutral-800" : "bg-neutral-200 text-neutral-500"
                  )}
                >
                  Continue
                </button>
                <div className="text-xs text-neutral-500">Next: choose style + layout</div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <div className="text-sm font-semibold">Options</div>
                <div className="mt-1 text-xs text-neutral-500">Reels output is 720×1280 (1080p later).</div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-neutral-200 p-4">
                  <div className="text-sm font-medium">Mode</div>
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => setMode("quick")}
                      className={cx(
                        "w-full rounded-2xl px-3 py-2 text-sm font-semibold ring-1",
                        mode === "quick" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white ring-neutral-200 hover:bg-neutral-50"
                      )}
                    >
                      Quick
                    </button>
                    <button
                      onClick={() => setMode("deep")}
                      className={cx(
                        "w-full rounded-2xl px-3 py-2 text-sm font-semibold ring-1",
                        mode === "deep" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white ring-neutral-200 hover:bg-neutral-50"
                      )}
                    >
                      Deep
                    </button>
                  </div>
                  <div className="mt-2 text-xs text-neutral-500">Quick = fewer scenes · Deep = more scenes</div>
                </div>

                <div className="rounded-2xl border border-neutral-200 p-4">
                  <div className="text-sm font-medium">Video Style</div>
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => setVideoStyle("education")}
                      className={cx(
                        "w-full rounded-2xl px-3 py-2 text-sm font-semibold ring-1",
                        videoStyle === "education" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white ring-neutral-200 hover:bg-neutral-50"
                      )}
                    >
                      Education
                    </button>
                    <button
                      onClick={() => setVideoStyle("business")}
                      className={cx(
                        "w-full rounded-2xl px-3 py-2 text-sm font-semibold ring-1",
                        videoStyle === "business" ? "bg-neutral-900 text-white ring-neutral-900" : "bg-white ring-neutral-200 hover:bg-neutral-50"
                      )}
                    >
                      Business
                    </button>
                  </div>
                  <div className="mt-2 text-xs text-neutral-500">Business = more formal palette + spacing</div>
                </div>

                <div className="rounded-2xl border border-neutral-200 p-4">
                  <div className="text-sm font-medium">Layout</div>
                  <div className="mt-3 rounded-2xl bg-neutral-50 px-3 py-2 text-sm font-semibold">
                    Reels (9:16) — 720×1280
                  </div>
                  <div className="mt-2 text-xs text-neutral-500">V1.5 exports reels only (laptop comes later)</div>
                </div>
              </div>

              {err ? <div className="text-sm text-red-700">{err}</div> : null}

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setStep("upload")}
                  className="rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-sm hover:bg-neutral-50"
                >
                  Back
                </button>
                <button
                  onClick={onGenerate}
                  disabled={busy}
                  className={cx(
                    "inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold",
                    busy ? "bg-neutral-200 text-neutral-500" : "bg-neutral-900 text-white hover:bg-neutral-800"
                  )}
                >
                  <Sparkles className="h-4 w-4" />
                  Generate
                </button>
                <div className="text-xs text-neutral-500">Creates scenes in parallel via Celery + Redis</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
