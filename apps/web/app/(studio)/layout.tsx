"use client";

import {useQueryClient} from "@tanstack/react-query";
import {useRouter} from "next/navigation";
import {useEffect} from "react";
import {usePathname} from "next/navigation";

import {Sidebar, TopBar} from "@/components/shell";
import {useAuthStore} from "@/lib/store";

/** Studio layout + auth guard for every /workspace surface. */
export default function StudioLayout({children}: {children: React.ReactNode}) {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const pathname = usePathname();
  const qc = useQueryClient();

  useEffect(() => {
    if (!token) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [token, router, pathname]);

  if (!token) return <div className="p-10 text-sm text-ink-300">Redirecting to login…</div>;

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
