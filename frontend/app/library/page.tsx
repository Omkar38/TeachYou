"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { JobCard } from "@/components/JobCard";
import { deleteJob, getLibrary, type LibraryJobItem } from "@/lib/api";

export default function LibraryPage() {
  const [items, setItems] = useState<LibraryJobItem[]>([]);
  const [toDelete, setToDelete] = useState<string | null>(null);

  async function reload() {
    const res = await getLibrary(30);
    setItems(res);
  }

  useEffect(() => {
    reload().catch(() => {
      // ignore
    });
  }, []);

  async function confirmDelete() {
    if (!toDelete) return;
    await deleteJob(toDelete);
    setToDelete(null);
    await reload();
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8">
      <div className="flex items-center gap-3">
        <div className="text-xl font-semibold">Library</div>
        <div className="text-sm text-neutral-600">Recent renders</div>
        <Link href="/" className="ml-auto text-sm underline">
          + New Video
        </Link>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => (
          <div key={it.id} className="relative">
            <JobCard job={it} thumbnailUrl={null} onDelete={() => setToDelete(it.id)} />
            <button
              className="absolute right-3 top-3 rounded-xl bg-white/90 p-2 ring-1 ring-neutral-200 hover:bg-white"
              onClick={() => setToDelete(it.id)}
              title="Delete"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={!!toDelete}
        title="Delete job"
        description="This removes generated assets for this job."
        confirmText="Delete"
        onCancel={() => setToDelete(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
