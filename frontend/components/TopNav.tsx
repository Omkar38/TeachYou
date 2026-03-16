"use client";

import Link from "next/link";
import { LogOut, Video } from "lucide-react";
import { clearToken, getToken } from "../lib/auth";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function TopNav({
  brandName = "SketchWave",
  subtitle = "PDF / Prompt → Whiteboard Video",
}: {
  brandName?: string;
  subtitle?: string;
} = {}) {
  const [hasToken, setHasToken] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setHasToken(Boolean(getToken()));
  }, []);

  function logout() {
    clearToken();
    setHasToken(false);
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-50 border-b bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-neutral-900 text-white shadow-soft">
            <Video size={18} />
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold">{brandName}</div>
            <div className="text-xs text-neutral-500">{subtitle}</div>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          {!hasToken ? (
            <Link
              href="/login"
              className="rounded-xl border px-3 py-2 text-sm font-medium hover:bg-neutral-50"
            >
              Login
            </Link>
          ) : (
            <button
              onClick={logout}
              className="inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium hover:bg-neutral-50"
            >
              <LogOut size={16} />
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
