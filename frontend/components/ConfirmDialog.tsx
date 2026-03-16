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
      className="rounded-2xl border border-neutral-200 bg-white p-0 shadow-soft backdrop:bg-black/30"
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
    >
      <div className="w-[min(92vw,520px)] p-6">
        <div className="text-lg font-semibold">{title}</div>
        {description ? <div className="mt-2 text-sm text-neutral-600">{description}</div> : null}
        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            className="rounded-xl border border-neutral-200 px-4 py-2 text-sm hover:bg-neutral-50"
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button
            className={
              "rounded-xl px-4 py-2 text-sm text-white " +
              (danger ? "bg-red-600 hover:bg-red-700" : "bg-neutral-900 hover:bg-neutral-800")
            }
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </dialog>
  );
}
