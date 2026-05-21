"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";

export type LibraryJobItem = {
  id: string;
  document_id: string;
  filename?: string | null;
  title?: string | null;
  created_at?: string | null;
  finished_at?: string | null;
  thumb_asset_id?: string | null;
  video_asset_id?: string | null;
  duration_sec?: number | null;
};

export function JobCard({
  job,
  thumbnailUrl,
  onDelete,
}: {
  job: LibraryJobItem;
  thumbnailUrl: string | null;
  onDelete: (job_id: string) => void;
}) {
  const title = job.title || job.filename || "Untitled video";
  const created = job.created_at
    ? new Date(job.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "";
  const dur = job.duration_sec && job.duration_sec > 0 ? formatDuration(job.duration_sec) : "";

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 transition-all duration-200 hover:border-violet-500/30 hover:bg-white/[0.08] hover:shadow-soft">
      <Link href={`/jobs/${job.id}`} className="block">
        {/* 9:16 thumbnail */}
        <div className="relative aspect-[9/16] w-full overflow-hidden bg-zinc-900">
          {thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={thumbnailUrl}
              alt={title}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-violet-950/30 to-zinc-900">
              <span className="text-4xl opacity-10">🎬</span>
            </div>
          )}
          {dur && (
            <div className="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 font-mono text-[10px] text-white backdrop-blur-sm">
              {dur}
            </div>
          )}
        </div>
        <div className="p-3">
          <div className="line-clamp-2 text-xs font-semibold text-zinc-200 transition-colors group-hover:text-white">
            {title}
          </div>
          {created && (
            <div className="mt-1 text-[10px] text-zinc-600">{created}</div>
          )}
        </div>
      </Link>

      {/* Delete button — appears on hover */}
      <button
        onClick={() => onDelete(job.id)}
        title="Delete"
        className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-lg bg-black/60 text-zinc-500 opacity-0 backdrop-blur-sm transition-all duration-150 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400"
      >
        <Trash2 size={12} />
      </button>
    </div>
  );
}

function formatDuration(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}
