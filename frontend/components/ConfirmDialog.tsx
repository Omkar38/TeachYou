"use client";

import { useEffect, useRef } from "react";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = "Delete",
  cancelText = "Cancel",
  danger = true,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const d = dialogRef.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="rounded-2xl border border-white/10 bg-zinc-900 p-0 shadow-soft"
      onCancel={(e) => { e.preventDefault(); onCancel(); }}
    >
      <div className="w-[min(92vw,480px)] p-6">
        <div className="text-base font-semibold text-white">{title}</div>
        {description && (
          <div className="mt-2 text-sm text-zinc-400">{description}</div>
        )}
        <div className="mt-6 flex items-center justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={
              "rounded-xl px-4 py-2 text-sm font-semibold text-white transition-all active:scale-[0.97] " +
              (danger ? "bg-red-500 hover:bg-red-600" : "bg-violet-500 hover:bg-violet-600 shadow-glow")
            }
          >
            {confirmText}
          </button>
        </div>
      </div>
    </dialog>
  );
}
