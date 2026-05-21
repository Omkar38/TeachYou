"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, Loader2, Sparkles, X } from "lucide-react";
import { cx } from "@/lib/utils";
import { promptAndCreateJob, uploadAndCreateJob } from "@/lib/api";

const ASPECT_RATIOS = [
  { value: "reels",     label: "9:16", sub: "Reels" },
  { value: "landscape", label: "16:9", sub: "YouTube" },
  { value: "square",    label: "1:1",  sub: "Feed" },
] as const;

const LENGTH_PRESETS = [
  { value: "quick",  label: "15–30s" },
  { value: "medium", label: "60s" },
  { value: "deep",   label: "3 min" },
] as const;

const CAPTION_STYLES = [
  { value: "off",      label: "No captions" },
  { value: "minimal",  label: "Minimal" },
  { value: "big_bold", label: "Big & Bold" },
] as const;

type AspectValue = (typeof ASPECT_RATIOS)[number]["value"];
type LengthValue = (typeof LENGTH_PRESETS)[number]["value"];
type CaptionValue = (typeof CAPTION_STYLES)[number]["value"];

const EXAMPLES = [
  "Explain quantum computing for beginners",
  "How intermittent fasting works — for TikTok",
  "The history of the Roman Empire in 60 seconds",
  "Why sleep is the most important habit",
];

const MODE_MAP: Record<LengthValue, "quick" | "deep"> = {
  quick: "quick",
  medium: "quick",
  deep: "deep",
};

const PRESET_MAP: Record<LengthValue, string> = {
  quick: "30s",
  medium: "60s",
  deep: "3m",
};

export default function HomePage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [aspect, setAspect] = useState<AspectValue>("reels");
  const [length, setLength] = useState<LengthValue>("quick");
  const [captions, setCaptions] = useState<CaptionValue>("minimal");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setPrompt(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 220) + "px";
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] || null;
    setFile(f);
    if (f) setPrompt("");
  }

  function clearFile() {
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function onGenerate() {
    const text = prompt.trim();
    if (!text && !file) { setErr("Add a prompt or upload a PDF."); return; }
    if (text && text.length < 10) { setErr("Add a bit more detail (10+ chars)."); return; }
    setErr(null);
    setBusy(true);
    try {
      const opts = { mode: MODE_MAP[length], layout: aspect, video_style: "business", length_preset: PRESET_MAP[length], caption_style: captions };
      let job_id: string;
      if (file) {
        ({ job_id } = await uploadAndCreateJob(file, opts));
      } else {
        ({ job_id } = await promptAndCreateJob(text, opts));
      }
      router.push(`/jobs/${job_id}`);
    } catch (e: any) {
      setErr(e?.message || "Something went wrong");
      setBusy(false);
    }
  }

  const canGenerate = !busy && (prompt.trim().length >= 10 || !!file);
  const examplePrompt = EXAMPLES[0];

  return (
    <div className="relative flex min-h-[calc(100vh-57px)] flex-col items-center justify-center overflow-hidden px-4 py-16">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-violet-600/10 blur-3xl" />

      <div className="relative w-full max-w-2xl animate-fade-in">
        {/* Heading */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            What do you want to{" "}
            <span className="gradient-text">make a video about?</span>
          </h1>
          <p className="mt-3 text-sm text-zinc-600">
            BYOK &middot; self-host &middot; no watermark &middot; GPU-free
          </p>
        </div>

        {/* Input card */}
        <div className="rounded-2xl border border-white/10 bg-white/5 shadow-soft backdrop-blur-sm transition-all duration-200 focus-within:border-violet-500/40 focus-within:shadow-glow">
          {file ? (
            <div className="flex items-center gap-3 px-4 py-4">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-violet-500/20 text-violet-400">
                <FileUp size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-white">{file.name}</div>
                <div className="text-xs text-zinc-500">{(file.size / 1024).toFixed(0)} KB · PDF</div>
              </div>
              <button
                onClick={clearFile}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg text-zinc-600 transition-colors hover:bg-white/10 hover:text-zinc-300"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={handleTextareaChange}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onGenerate(); }}
              className="min-h-[100px] w-full resize-none bg-transparent px-4 pb-12 pt-4 text-sm text-white placeholder-zinc-600 outline-none"
              placeholder={`E.g. "${examplePrompt}"`}
              rows={3}
            />
          )}

          {/* Bottom row inside card */}
          <div className="flex items-center justify-between border-t border-white/5 px-3 py-2">
            <label className="flex cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-zinc-500 transition-colors hover:bg-white/5 hover:text-zinc-300">
              <FileUp size={13} />
              {file ? "Change PDF" : "Upload PDF"}
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>
            <span className="text-xs text-zinc-700">
              {!file && prompt.length > 0 ? `${prompt.length} chars` : "⌘↵ to generate"}
            </span>
          </div>
        </div>

        {/* Chips row */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-zinc-600">Format</span>
          {ASPECT_RATIOS.map((ar) => (
            <button
              key={ar.value}
              onClick={() => setAspect(ar.value)}
              className={cx(
                "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
                aspect === ar.value
                  ? "border-violet-500/60 bg-violet-500/20 text-violet-300"
                  : "border-white/10 bg-white/5 text-zinc-500 hover:border-white/20 hover:text-zinc-300"
              )}
            >
              <span className="font-mono">{ar.label}</span>
              <span className="ml-1.5 opacity-60">{ar.sub}</span>
            </button>
          ))}
          <div className="mx-1 h-4 w-px bg-white/10" />
          <span className="text-xs text-zinc-600">Length</span>
          {LENGTH_PRESETS.map((lp) => (
            <button
              key={lp.value}
              onClick={() => setLength(lp.value)}
              className={cx(
                "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
                length === lp.value
                  ? "border-violet-500/60 bg-violet-500/20 text-violet-300"
                  : "border-white/10 bg-white/5 text-zinc-500 hover:border-white/20 hover:text-zinc-300"
              )}
            >
              {lp.label}
            </button>
          ))}
          <div className="mx-1 h-4 w-px bg-white/10" />
          <span className="text-xs text-zinc-600">Captions</span>
          {CAPTION_STYLES.map((cs) => (
            <button
              key={cs.value}
              onClick={() => setCaptions(cs.value)}
              className={cx(
                "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
                captions === cs.value
                  ? "border-violet-500/60 bg-violet-500/20 text-violet-300"
                  : "border-white/10 bg-white/5 text-zinc-500 hover:border-white/20 hover:text-zinc-300"
              )}
            >
              {cs.label}
            </button>
          ))}
        </div>

        {/* Error */}
        {err && (
          <div className="mt-3 rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            {err}
          </div>
        )}

        {/* Generate button */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={onGenerate}
            disabled={!canGenerate}
            className={cx(
              "inline-flex items-center gap-2.5 rounded-xl px-8 py-3.5 text-sm font-semibold transition-all duration-200",
              canGenerate
                ? "bg-violet-500 text-white shadow-glow hover:bg-violet-600 active:scale-[0.97]"
                : "cursor-not-allowed bg-white/5 text-zinc-600"
            )}
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {busy ? "Generating…" : "Generate Video"}
          </button>
        </div>

        {/* Example prompts */}
        {!prompt && !file && !busy && (
          <div className="mt-10 text-center">
            <div className="mb-3 text-xs text-zinc-700">Try an example</div>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLES.slice(0, 3).map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setPrompt(p);
                    setTimeout(() => {
                      if (textareaRef.current) {
                        textareaRef.current.style.height = "auto";
                        textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
                        textareaRef.current.focus();
                      }
                    }, 0);
                  }}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-500 transition-all hover:border-violet-500/30 hover:text-zinc-300"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
