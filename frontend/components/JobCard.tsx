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
  const title = job.title || job.filename || "Untitled explainer";
  const subtitle = job.filename ? `${job.filename}` : job.document_id;
  const created = job.created_at ? new Date(job.created_at).toLocaleString() : "";
  const dur = job.duration_sec && job.duration_sec > 0 ? formatDuration(job.duration_sec) : "";

  return (
    <div className="group rounded-2xl border border-neutral-200 bg-white shadow-soft overflow-hidden">
      <Link href={`/jobs/${job.id}`} className="block">
        <div className="aspect-video w-full bg-neutral-100 relative">
          {thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={thumbnailUrl} alt={title} className="h-full w-full object-cover" />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-neutral-100 to-neutral-200" />
          )}
          {dur ? (
            <div className="absolute bottom-2 right-2 rounded-lg bg-black/70 px-2 py-1 text-xs text-white">
              {dur}
            </div>
          ) : null}
        </div>
        <div className="p-4">
          <div className="line-clamp-2 text-sm font-semibold text-neutral-900 group-hover:underline">
            {title}
          </div>
          <div className="mt-1 line-clamp-1 text-xs text-neutral-600">{subtitle}</div>
          <div className="mt-1 text-xs text-neutral-500">{created}</div>
        </div>
      </Link>
      <div className="px-4 pb-4">
        <button
          className="inline-flex items-center gap-2 rounded-xl border border-neutral-200 px-3 py-2 text-xs hover:bg-neutral-50"
          onClick={() => onDelete(job.id)}
        >
          <Trash2 size={14} />
          Delete
        </button>
      </div>
    </div>
  );
}

function formatDuration(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  return `${m}:${String(r).padStart(2, "0")}`;
}
