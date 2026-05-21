"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { JobCard } from "@/components/JobCard";
import { deleteJob, getLibrary, type LibraryJobItem } from "@/lib/api";

export default function LibraryPage() {
  const [items, setItems] = useState<LibraryJobItem[]>([]);
  const [toDelete, setToDelete] = useState<string | null>(null);

  async function reload() {
    try { setItems(await getLibrary(30)); } catch {}
  }

  useEffect(() => { reload(); }, []);

  async function confirmDelete() {
    if (!toDelete) return;
    await deleteJob(toDelete);
    setToDelete(null);
    await reload();
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Library</h1>
          <p className="mt-0.5 text-xs text-zinc-600">
            {items.length > 0 ? `${items.length} video${items.length !== 1 ? "s" : ""}` : "Your generated videos"}
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 rounded-xl bg-violet-500 px-4 py-2.5 text-sm font-semibold text-white shadow-glow transition-all hover:bg-violet-600 active:scale-[0.97]"
        >
          <Plus size={15} />
          New Video
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="mt-24 flex flex-col items-center gap-4 text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-5xl">
            🎬
          </div>
          <div className="text-base font-semibold text-zinc-300">No videos yet</div>
          <p className="text-sm text-zinc-600">Create your first video to see it here</p>
          <Link
            href="/"
            className="mt-2 rounded-xl bg-violet-500 px-5 py-2.5 text-sm font-semibold text-white shadow-glow hover:bg-violet-600"
          >
            Create a video
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {items.map((it) => (
            <JobCard
              key={it.id}
              job={it}
              thumbnailUrl={null}
              onDelete={() => setToDelete(it.id)}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!toDelete}
        title="Delete video?"
        description="All generated assets for this job will be permanently removed."
        confirmText="Delete"
        onCancel={() => setToDelete(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
