"use client";

import { useEffect, useState } from "react";
import { Check, KeyRound, Save } from "lucide-react";
import { clearToken, getToken, setToken } from "../../lib/auth";

export default function LoginPage() {
  const [token, setTokenState] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (t) setTokenState(t);
  }, []);

  function onSave() {
    if (token.trim()) { setToken(token.trim()); } else { clearToken(); }
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-soft backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/20 text-violet-400">
              <KeyRound size={18} />
            </div>
            <div>
              <div className="text-base font-semibold text-white">Authentication</div>
              <div className="text-xs text-zinc-500">Set your API access token</div>
            </div>
          </div>

          <div className="mt-6">
            <label className="text-xs font-medium text-zinc-400">Token</label>
            <input
              className="mt-2 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.08]"
              placeholder="dev-token"
              value={token}
              onChange={(e) => setTokenState(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSave()}
            />
            <div className="mt-1.5 text-[11px] text-zinc-600">Leave blank to clear the stored token.</div>
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={onSave}
              className="inline-flex items-center gap-2 rounded-xl bg-violet-500 px-5 py-2.5 text-sm font-semibold text-white shadow-glow transition-all hover:bg-violet-600 active:scale-[0.97]"
            >
              <Save size={14} /> Save
            </button>
            {saved && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <Check size={12} /> Saved
              </span>
            )}
            <a href="/" className="ml-auto text-xs text-zinc-600 transition-colors hover:text-zinc-300">
              Back to home
            </a>
          </div>

          <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-4 text-[11px] text-zinc-500">
            <div className="mb-1 font-medium text-zinc-400">Default token</div>
            Start the backend with{" "}
            <code className="rounded bg-white/10 px-1 py-0.5 text-zinc-300">DEV_TOKEN=dev-token</code>
            , then enter{" "}
            <code className="rounded bg-white/10 px-1 py-0.5 text-zinc-300">dev-token</code> here.
          </div>
        </div>
      </div>
    </div>
  );
}
