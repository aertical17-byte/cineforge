"use client";

import {useQuery} from "@tanstack/react-query";

import {jsonApi} from "@/lib/api";
import {Badge, Card} from "@/components/ui";

type Row = {id: string; name: string; category?: string; motion_strength?: number; fragment?: string};

export default function PresetsPage() {
  const registry = useQuery({queryKey: ["registry", "camera_moves"], queryFn: () => jsonApi<Row[]>("/v1/registry/camera_moves", "GET")});
  const styles = useQuery({queryKey: ["registry", "palettes"], queryFn: () => jsonApi<Row[]>("/v1/registry/palettes", "GET")});
  const imageStyles = useQuery({queryKey: ["registry", "image_style_presets"], queryFn: () => jsonApi<Row[]>("/v1/registry/image_style_presets", "GET")});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Presets</h1>
        <p className="text-sm text-ink-300">The shared registries every studio uses. Categories are generic cinematography vocabulary — the composition engine adapts per model.</p>
      </div>

      <Section title="Camera moves" rows={registry.data} render={(r) => r.fragment ?? ""} />

      <Card className="p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-300">Color palettes</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
          {(styles.data ?? []).map((p) => (
            <div key={p.id} className="rounded-lg border border-ink-600 bg-ink-900 p-3 text-xs text-ink-100">{p.name}</div>
          ))}
        </div>
      </Card>

      <Section title="Image style presets" rows={imageStyles.data} render={(r) => (r as {fragment?: string}).fragment ?? ""} />
    </div>
  );
}

function Section({title, rows, render}: {title: string; rows?: Row[]; render: (r: Row) => string}) {
  return (
    <Card className="p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-300">{title}</h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {(rows ?? []).map((r) => (
          <div key={r.id} className="rounded-lg border border-ink-700 bg-ink-900 p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium" data-testid={`preset-${r.id}`}>{r.name}</span>
              {r.category && <Badge tone="neutral">{r.category}</Badge>}
            </div>
            <p className="mt-1 line-clamp-2 text-[11px] text-ink-300">{render(r)}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
