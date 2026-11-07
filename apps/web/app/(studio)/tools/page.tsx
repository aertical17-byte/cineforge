"use client";

import Link from "next/link";
import {Card} from "@/components/ui";

const TOOLS = [
  {href: "/create/image", icon: "🖼", name: "Image studio", body: "Text→image, batches, seeds, style presets."},
  {href: "/create/video", icon: "🎬", name: "Video studio", body: "Text or first-frame→video with camera presets."},
  {href: "/create/edit", icon: "🪄", name: "Enhance & edit", body: "Upscale images; regional video edits on supported engines."},
  {href: "/presets", icon: "✦", name: "Camera & film presets", body: "22 camera moves, palettes, lighting, speed ramps."},
  {href: "/characters", icon: "👤", name: "Characters", body: "Train consistent identities from photo sets."},
  {href: "/library", icon: "▦", name: "Library", body: "Every asset with search, filters, download, re-rolls."},
];

export default function ToolsHub() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Toolbox</h1>
        <p className="text-sm text-ink-300">Every creative surface in one place.</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {TOOLS.map((t) => (
          <Link key={t.href} href={t.href} data-testid={`tool-${t.name.split(" ")[0].toLowerCase()}`}>
            <Card className="h-full p-5 transition hover:border-byz-500/40">
              <div className="mb-2 text-2xl">{t.icon}</div>
              <h3 className="font-medium">{t.name}</h3>
              <p className="mt-1 text-xs text-ink-300">{t.body}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
