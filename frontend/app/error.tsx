"use client";

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="rounded-2xl bg-zinc-900/60 p-6 ring-1 ring-zinc-800">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <pre className="mt-3 overflow-auto rounded-xl bg-zinc-950 p-3 text-xs text-zinc-200 ring-1 ring-zinc-800">
        {error.message}
      </pre>
      <button
        onClick={() => reset()}
        className="mt-4 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500"
      >
        Retry
      </button>
    </div>
  );
}
