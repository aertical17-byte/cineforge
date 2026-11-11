"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect} from "react";
import {useQuery} from "@tanstack/react-query";

import {jsonApi} from "@/lib/api";
import type {Asset} from "@/lib/types";
import {useAuthStore} from "@/lib/store";
import {Badge} from "@/components/ui";

const NAV = [
  {section: "Create", links: [
    {href: "/create/image", label: "Image", icon: "🖼"},
    {href: "/create/video", label: "Video", icon: "🎬"},
    {href: "/create/edit", label: "Edit & Enhance", icon: "🪄"},
    {href: "/flowboard", label: "Flowboard", icon: "⛓"},
  ]},
  {section: "Work", links: [
    {href: "/dashboard", label: "Dashboard", icon: "◈"},
    {href: "/projects", label: "Projects", icon: "🗂"},
    {href: "/library", label: "Library", icon: "▦"},
    {href: "/history", label: "History", icon: "⟲"},
  ]},
  {section: "Inspiration", links: [
    {href: "/presets", label: "Presets", icon: "✦"},
    {href: "/templates", label: "Templates", icon: "🌀"},
    {href: "/characters", label: "Characters", icon: "👤"},
    {href: "/tools", label: "Toolbox", icon: "🧰"},
  ]},
];

export function Sidebar() {
  const path = usePathname();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-ink-700 bg-ink-900" data-testid="sidebar">
      <Link href="/dashboard" className="flex items-center gap-2 px-5 py-5" data-testid="logo">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-byz-500 text-sm font-bold text-white">CF</span>
        <span className="text-[15px] font-semibold tracking-tight">CineForge</span>
      </Link>
      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {NAV.map((sec) => (
          <div key={sec.section} className="mb-4">
            <div className="px-2 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-widest text-ink-300">{sec.section}</div>
            {sec.links.map((l) => {
              const active = path === l.href || path.startsWith(l.href + "?");
              return (
                <Link key={l.href} href={l.href}
                  className={`mb-0.5 flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition ${active ? "bg-byz-500/15 text-byz-200" : "text-ink-200 hover:bg-ink-800"}`}>
                  <span className="w-4 text-center text-[13px]">{l.icon}</span>{l.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="border-t border-ink-700 p-3">
        <Link href="/settings/profile" className="block rounded-lg px-2.5 py-2 text-sm text-ink-200 hover:bg-ink-800">⚙️ Settings</Link>
        {user?.is_admin && (
          <Link href="/admin" className="block rounded-lg px-2.5 py-2 text-sm text-ink-200 hover:bg-ink-800">🛡 Admin</Link>
        )}
        <button onClick={logout} className="w-full rounded-lg px-2.5 py-2 text-left text-sm text-ink-300 hover:bg-ink-800">↪ Sign out</button>
      </div>
    </aside>
  );
}

export function TopBar() {
  const {user} = useAuthStore();
  const credits = useQuery({
    queryKey: ["credits"],
    queryFn: () => jsonApi<{balance: number}>("/v1/credits/summary", "GET"),
    refetchInterval: 15000,
  });
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-end gap-3 border-b border-ink-700 bg-ink-950/80 px-5 backdrop-blur">
      {user && (
        <Link href="/settings/subscription" data-testid="credits-badge" title="Your credit balance">
          <Badge tone="accent">{credits.data?.balance ?? "·"} credits</Badge>
        </Link>
      )}
      <Link href="/create/image" className="text-ink-100"><Badge tone="neutral">＋ New generation</Badge></Link>
    </header>
  );
}

/** Like-manager for the workspace layout: keeps react-query fresh when generations complete. */
export function FeedbackRefresher({onTick}: {onTick: () => void}) {
  useEffect(() => {
    const id = setInterval(onTick, 4000);
    return () => clearInterval(id);
  }, [onTick]);
  return null;
}

export function useLibraryPreview(fetchAssets: () => Promise<Asset[]>) {
  return useQuery({queryKey: ["assets", "panel"], queryFn: fetchAssets});
}
