"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Library, LogOut, Zap } from "lucide-react";
import { clearToken, getToken } from "../lib/auth";

export function TopNav() {
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
    <header className="sticky top-0 z-50 border-b border-white/10 bg-zinc-950/80 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5 group">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500 text-white shadow-glow-sm transition-shadow group-hover:shadow-glow">
            <Zap size={15} className="fill-white" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-white">TeachYou</span>
        </Link>

        <nav className="flex items-center gap-1">
          <Link
            href="/library"
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Library size={14} />
            Library
          </Link>

          {!hasToken ? (
            <Link
              href="/login"
              className="ml-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
            >
              Login
            </Link>
          ) : (
            <button
              onClick={logout}
              className="ml-1 flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
            >
              <LogOut size={14} />
              Logout
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
