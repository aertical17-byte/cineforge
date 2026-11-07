"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import Link from "next/link";
import {useState} from "react";

import {jsonApi} from "@/lib/api";
import type {Project} from "@/lib/types";
import {Badge, Button, Card, EmptyState, Input} from "@/components/ui";

export default function ProjectsPage() {
  const qc = useQueryClient();
  const projects = useQuery({queryKey: ["projects"], queryFn: () => jsonApi<Project[]>("/v1/projects", "GET")});
  const [name, setName] = useState("");
  const rename = useMutation({
    mutationFn: (p: {id: string; name: string}) => jsonApi<Project>(`/v1/projects/${p.id}`, "PATCH", {name: p.name}),
    onSuccess: () => qc.invalidateQueries({queryKey: ["projects"]}),
  });
  const remove = useMutation({
    mutationFn: (id: string) => jsonApi<null>(`/v1/projects/${id}`, "DELETE"),
    onSuccess: () => qc.invalidateQueries({queryKey: ["projects"]}),
  });
  const create = useMutation({
    mutationFn: () => jsonApi<Project>("/v1/projects", "POST", {name}),
    onSuccess: () => {
      setName("");
      qc.invalidateQueries({queryKey: ["projects"]});
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-ink-300">Group generations, uploads and references per production.</p>
        </div>
      </div>
      <Card className="flex gap-2 p-4">
        <Input data-testid="new-project" placeholder="New project name…" value={name} onChange={(e) => setName(e.target.value)} />
        <Button data-testid="create-project" disabled={!name} onClick={() => create.mutate()}>Create</Button>
      </Card>

      {projects.data && projects.data.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.data.map((p) => (
            <Card key={p.id} className="flex flex-col p-4" data-testid="project-card">              <div className="flex items-start justify-between">
                <Link href={`/projects/${p.id}`} className="font-medium hover:text-byz-200">{p.name}</Link>
                {p.is_archived && <Badge tone="warn">archived</Badge>}
              </div>
              <p className="mt-1 line-clamp-2 min-h-8 text-xs text-ink-300">{p.description || "· no description ·"}</p>
              <div className="mt-3 flex items-center justify-between border-t border-ink-700 pt-3">
                <span className="text-[11px] text-ink-300">{new Date(p.updated_at).toLocaleDateString()}</span>
                <div className="flex gap-1.5">
                  <Button size="sm" variant="ghost" onClick={() => {
                    const newName = prompt("Rename project", p.name);
                    if (newName) rename.mutate({id: p.id, name: newName});
                  }}>Rename</Button>
                  <Button size="sm" variant="ghost" data-testid={`delete-${p.id}`} onClick={() => remove.mutate(p.id)}>Delete</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title="No projects" body="Create your first project to start organizing generations." />
      )}
    </div>
  );
}

