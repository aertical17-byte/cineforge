"use client";

import {useQuery} from "@tanstack/react-query";
import Link from "next/link";
import {useEffect, useState} from "react";

import {jsonApi} from "@/lib/api";
import type {Asset} from "@/lib/types";
import {Badge, Card, EmptyState, Input, Tabs} from "@/components/ui";

export default function LibraryPage() {
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<Asset[]>([]);
  const [next, setNext] = useState<string | null>(null);

  const qs = new URLSearchParams({limit: "48"});
  if (kind) qs.set("kind", kind);
  if (search) qs.set("search", search);

  const first = useQuery({queryKey: ["assets", "lib", kind, search], queryFn: () => jsonApi<{items: Asset[]; next: string | null}>(`/v1/assets?${qs}`, "GET")});

  useEffect(() => {
    if (first.data) {
      setItems(first.data.items);
      setNext(first.data.next);
    }
  }, [first.data]);

  const loadMore = async () => {
    if (!next) return;
    const data = await jsonApi<{items: Asset[]; next: string | null}>(`/v1/assets?${qs}&cursor=${next}`, "GET");
    setItems((cur) => [...cur, ...data.items]);
    setNext(data.next);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Library</h1>
          <p className="text-sm text-ink-300">Every upload and generation. Hover for actions; click to open.</p>
        </div>
        <Tabs items={[{id: "", label: "All"}, {id: "image", label: "Images"}, {id: "video", label: "Videos"}]}
          active={kind} onChange={setKind} />
      </div>
      <Input placeholder="Search by file or prompt text…" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-md" data-testid="library-search" />

      {items.length === 0 ? (
        <EmptyState title="Nothing here yet" body="Run your first generation — results will automatically land here." />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {items.map((a) => (
            <div key={a.id} className="group relative overflow-hidden rounded-xl border border-ink-700 bg-ink-850" data-testid="library-item">
              <div className="aspect-square">
                {a.kind === "video"
                  ? <video className="h-full w-full object-cover" src={a.url} muted />
                  : /* eslint-disable-next-line @next/next/no-img-element */
                  <img className="h-full w-full object-cover" src={a.url} alt="asset" loading="lazy" />}
              </div>
              <div className="absolute inset-x-0 bottom-0 hidden items-center justify-between bg-gradient-to-t from-black/80 to-transparent p-2 group-hover:flex">
                <a href={a.url} download target="_blank" rel="noreferrer" className="text-[11px] text-white underline">download</a>
                <Badge tone={a.source === "upload" ? "neutral" : "accent"}>{a.source}</Badge>
              </div>
            </div>
          ))}
        </div>
      )}
      {next && (
        <div className="text-center">
          <button className="rounded-xl border border-ink-600 px-5 py-2.5 text-sm hover:border-byz-400" onClick={loadMore}>Load more</button>
        </div>
      )}
      {!first.isFetching && items.length === 0 && (
        <Card className="p-4 text-sm text-ink-300">Tip: the <Link className="text-byz-300 underline" href="/create/image">image studio</Link> is the fastest way to start.</Card>
      )}
    </div>
  );
}
