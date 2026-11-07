"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {useState} from "react";

import {jsonApi} from "@/lib/api";
import type {Generation} from "@/lib/types";
import {Badge, Button, Card, EmptyState} from "@/components/ui";

export default function HistoryPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState<string | null>(null);
  const gens = useQuery({
    queryKey: ["history", "full"],
    queryFn: () => jsonApi<{items: Generation[]}>("/v1/generations?limit=50", "GET"),
    refetchInterval: 5000,
  });

  const reroll = useMutation({
    mutationFn: (id: string) => jsonApi<Generation>(`/v1/generations/${id}/reroll`, "POST"),
    onSuccess: () => qc.invalidateQueries({queryKey: ["history", "full"]}),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Generation history</h1>
        <p className="text-sm text-ink-300">Full audit trail of every run with exact settings — re-roll any item.</p>
      </div>
      {gens.data?.items.length ? (
        <div className="space-y-2">
          {gens.data.items.map((g) => (
            <Card key={g.id} className="p-4" data-testid="history-row">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <button className="max-w-[60%] truncate text-left text-sm" onClick={() => setOpen(open === g.id ? null : g.id)}>
                  <span className="mr-2 text-ink-300">#{g.id.slice(0, 6)}</span>
                  {g.prompt.slice(0, 70)}
                </button>
                <div className="flex items-center gap-2 text-xs text-ink-300">
                  <Badge tone={g.status === "succeeded" ? "ok" : g.status === "failed" ? "err" : "accent"} data-testid="gen-status">{g.status}</Badge>
                  <span>{g.model_id}</span>
                  <span>−{g.actual_credits || g.estimated_credits} cr</span>
                  <Button size="sm" variant="outline" onClick={() => reroll.mutate(g.id)} data-testid="reroll">Re-roll</Button>
                </div>
              </div>
              {open === g.id && (
                <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-ink-900 p-3 text-[11px] text-ink-200">
{JSON.stringify({model: g.model_id, task: g.task, params: g.params}, null, 2)}
                </pre>
              )}
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title="No history" body="Everything you generate is remembered with its exact settings here." />
      )}
    </div>
  );
}
