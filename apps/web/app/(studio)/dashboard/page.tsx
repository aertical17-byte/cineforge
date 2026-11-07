"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import Link from "next/link";
import {useState} from "react";

import {jsonApi} from "@/lib/api";
import {useAuthStore} from "@/lib/store";
import type {Asset, Generation, Project} from "@/lib/types";
import {Badge, Button, Card, EmptyState, Field, Input} from "@/components/ui";

export default function Dashboard() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();

  const gens = useQuery({queryKey: ["history", "recent"], queryFn: () => jsonApi<{items: Generation[]}>("/v1/generations?limit=8", "GET")});
  const assets = useQuery({queryKey: ["assets", "recent"], queryFn: () => jsonApi<{items: Asset[]}>("/v1/assets?limit=8", "GET")});
  const projects = useQuery({queryKey: ["projects"], queryFn: () => jsonApi<Project[]>("/v1/projects", "GET")});
  const credits = useQuery({queryKey: ["credits"], queryFn: () => jsonApi<{balance: number}>("/v1/credits/summary", "GET")});

  const [name, setName] = useState("");
  const createProject = useMutation({
    mutationFn: () => jsonApi<Project>("/v1/projects", "POST", {name}),
    onSuccess: () => {
      setName("");
      void qc.invalidateQueries({queryKey: ["projects"]});
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" data-testid="dashboard-title">
            Welcome{(user?.display_name ? ", " + user.display_name : "")}
          </h1>
          <p className="text-sm text-ink-300">Your studio at a glance.</p>
        </div>
        <Badge tone="accent">{credits.data?.balance ?? "·"} credits</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Credits" value={String(credits.data?.balance ?? "–")} href="/settings/subscription" />
        <Stat label="Projects" value={String(projects.data?.length ?? 0)} href="/projects" />
        <Stat label="Library items" value={String(assets.data?.items.length ?? 0)} href="/library" />
        <Stat label="Runs today" value={String(gens.data?.items.filter((g) => g.created_at.startsWith(new Date().toISOString().slice(0, 10))).length ?? 0)} href="/history" />
      </div>

      <Card className="p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-300">Create a new project</h2>
        <div className="flex max-w-xl gap-2">
          <Input data-testid="project-name" placeholder="Campaign name…" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && name && createProject.mutate()} />
          <Button data-testid="project-create" disabled={!name || createProject.isPending} onClick={() => createProject.mutate()}>Create</Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-300">Recent runs</h2>
            <Link href="/history" className="text-xs text-byz-300 underline">All history</Link>
          </div>
          <div className="space-y-2">
            {(gens.data?.items ?? []).map((g) => (
              <div key={g.id} className="flex items-center justify-between rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-sm">
                <span className="truncate pr-3 text-ink-100">{g.prompt.slice(0, 60) || g.task}</span>
                <Badge tone={g.status === "succeeded" ? "ok" : g.status === "failed" ? "err" : "accent"}>{g.status}</Badge>
              </div>
            ))}
            {!gens.data?.items.length && <EmptyState title="No runs yet" body="Generate your first image or video to fill this feed." />}
          </div>
        </Card>
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-300">Latest assets</h2>
            <Link href="/library" className="text-xs text-byz-300 underline">Open library</Link>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {(assets.data?.items ?? []).map((a) => (
              <div key={a.id} className="aspect-square overflow-hidden rounded-lg border border-ink-600">
                {a.kind === "video"
                  ? <video className="h-full w-full object-cover" src={a.url} />
                  : /* eslint-disable-next-line @next/next/no-img-element */
                  <img className="h-full w-full object-cover" src={a.url} alt="asset" />}
              </div>
            ))}
            {!assets.data?.items.length && <p className="col-span-4 text-sm text-ink-300">Assets appear here as soon as they exist.</p>}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Stat({label, value, href}: {label: string; value: string; href: string}) {
  return (
    <Link href={href} className="rounded-xl2 border border-ink-700 bg-ink-850 p-4 transition hover:border-byz-500/40">
      <div className="text-xs text-ink-300">{label}</div>
      <div className="mt-1 text-2xl font-semibold" data-testid={`stat-${label.toLowerCase().replace(/ /g, "-")}`}>{value}</div>
    </Link>
  );
}
