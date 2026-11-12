"use client";

import {useEffect} from "react";

import {Sidebar, TopBar} from "@/components/shell";
import {ensureGuestSession} from "@/lib/guest";
import {useAuthStore} from "@/lib/store";

/**
 * Studio layout + auth gate for every /workspace surface.
 * No-login mode: instead of redirecting to /login, an ephemeral guest session is minted
 * automatically (POST /v1/auth/guest) on first visit. If the API is unreachable we say so
 * honestly instead of pretending the studio is fine.
 */
export default function StudioLayout({children}: {children: React.ReactNode}) {
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);

  useEffect(() => {
    if (hydrated && !token) {
      void ensureGuestSession().catch(() => undefined);
    }
  }, [hydrated, token]);

  if (!hydrated) return <div className="p-10 text-sm text-ink-300">Loading studio…</div>;
  if (!token) {
    return (
      <div className="p-10 text-sm text-ink-200">
        <p>Preparing your guest session…</p>
        <p className="mt-2 text-ink-300">
          If this stays stuck, the API is not reachable — start the services (docker compose up) and reload.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        <TopBar />
        <main className="flex-1 px-5 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
