"use client";

import {useQuery} from "@tanstack/react-query";

import {jsonApi} from "@/lib/api";
import {Badge, Card, EmptyState} from "@/components/ui";

type Template = {
  id: string; slug: string; name: string; category: string; media_type: string;
  prompt: string; settings: Record<string, any>;
};

export default function TemplatesPage() {
  const t = useQuery({queryKey: ["templates"], queryFn: () => jsonApi<Template[]>("/v1/templates", "GET")});
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Templates</h1>
        <p className="text-sm text-ink-300">Curated starting points: prompt + engine + camera + film setup, one click into a studio.</p>
      </div>
      {t.data && t.data.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {t.data.map((tpl) => (
            <Card key={tpl.id} className="flex flex-col p-5" data-testid="template-card">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-medium">{tpl.name}</h3>
                <Badge tone={tpl.media_type === "video" ? "accent" : "neutral"}>{tpl.media_type}</Badge>
              </div>
              <p className="mb-3 text-xs text-ink-200 line-clamp-3">{tpl.prompt}</p>
              <pre className="mt-auto max-h-24 overflow-auto rounded-lg bg-ink-900 p-2 text-[10px] text-ink-300">
{JSON.stringify(tpl.settings, null, 1)}
              </pre>
              <a
                href={`/create/${tpl.media_type}?template=${tpl.slug}`}
                className="mt-3 rounded-xl bg-byz-500 px-4 py-2 text-center text-sm font-medium text-white hover:bg-byz-400">
                Open in {tpl.media_type} studio
              </a>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title="Templates load after first run" body="Curated configurations appear once the registry is available." />
      )}
    </div>
  );
}
