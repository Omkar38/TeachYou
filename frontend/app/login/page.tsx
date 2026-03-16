"use client";

import { useEffect, useState } from "react";
import { KeyRound, Save } from "lucide-react";
import { clearToken, getToken, setToken } from "../../lib/auth";

export default function LoginPage() {
  const [token, setTokenState] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (t) setTokenState(t);
  }, []);

  function onSave() {
    if (token.trim()) {
      setToken(token.trim());
    } else {
      clearToken();
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-soft">
        <div className="flex items-center gap-2 text-xl font-bold">
          <KeyRound size={20} />
          Auth
        </div>
        <div className="mt-2 text-sm text-neutral-600">
          This UI uses a single token to call the backend. The backend checks <code className="rounded bg-neutral-100 px-1">API_AUTH_TOKEN</code>.
        </div>

        <div className="mt-6">
          <label className="text-sm font-medium text-neutral-700">Token</label>
          <input
            className="mt-2 w-full rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-neutral-900"
            placeholder="dev-token"
            value={token}
            onChange={(e) => setTokenState(e.target.value)}
          />
          <div className="mt-2 text-xs text-neutral-500">
            Leave blank to clear the token.
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3">
          <button
            onClick={onSave}
            className="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white shadow-soft hover:bg-neutral-800"
          >
            <Save size={16} />
            Save
          </button>
          {saved ? <span className="text-sm text-green-700">Saved ✓</span> : null}
          <a className="ml-auto text-sm underline" href="/">
            Back to library
          </a>
        </div>

        <div className="mt-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-700">
          <div className="font-medium">Backend defaults</div>
          <div className="mt-1">If you run the backend with <code className="rounded bg-white px-1">API_AUTH_TOKEN=dev-token</code>, you can use <code className="rounded bg-white px-1">dev-token</code> here.</div>
        </div>
      </div>
    </div>
  );
}
