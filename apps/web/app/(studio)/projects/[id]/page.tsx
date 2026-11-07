"use client";

import Link from "next/link";
import {useParams} from "next/navigation";
import {useQuery} from "@tanstack/react-query";

import {jsonApi} from "@/lib/api";
import type {Asset, Generation, Project} from "@/lib/types";
import {Badge, Card, EmptyState} from "@/components/ui";

export default function ProjectDetail() {
  const {id} = useParams<{id: string}>();
  const project = useQuery({queryKey: ["project", id], queryFn: () => jsonApi<Project>(`/v1/projects/${id}`, "GET")});
  const gens = useQuery({queryKey: ["gens", id], queryFn: () => jsonApi<{items: Generation[]}>(`/v1/generations?project_id=${id}`, "GET")});
  const assets = useQuery({queryKey: ["assets", id], queryFn: () => jsonApi<{items: Asset[]}>(`/v1/assets?project_id=${id}&limit=100`, "GET")});

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <Link href="/projects" className="text-xs text-ink-300 underline">← Projects</Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{project.data?.name ?? "…"}</h1>
        </div>
        <Badge tone="neutral">{assets.data?.items.length ?? 0} assets</Badge>
      </div>

      <Card className="p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-300">Generations</h2>
        {(gens.data?.items ?? []).length ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {gens.data.items.flatMap((g) =>
              (assets.data?.items ?? []).filter((a) => a.generation_id === g.id).map((a) => (
                <div key={a.id} className="overflow-hidden rounded-xl border border-ink-600">
                  {a.kind === "video" ? (
                    <video className="w-full" src={a.url} controls />
                  ) : (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img className="w-full" src={a.url} alt="generation" />
                  )}
                  <p className="p-2 text-[11px] text-ink-300">{g.model_id} · {g.status}</p>
                </div>
              )),
            )}
          </div>
        ) : (
          <EmptyState title="Empty project" body="Generate into this project from the image or video studio." />
        )}
      </Card>
    </div>
  );
}
