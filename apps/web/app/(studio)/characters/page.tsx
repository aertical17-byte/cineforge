"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {useState} from "react";

import {jsonApi, rawUpload} from "@/lib/api";
import type {Asset} from "@/lib/types";
import {useAuthStore} from "@/lib/store";
import {Badge, Button, Card, EmptyState, Field, Input} from "@/components/ui";

type Element = {id: string; type: string; name: string; description: string; training_status: string; attributes: Record<string, any>};

export default function CharactersPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const elements = useQuery({queryKey: ["elements"], queryFn: () => jsonApi<Element[]>("/v1/elements?type=character", "GET")});
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [photos, setPhotos] = useState<Asset[]>([]);
  const [notice, setNotice] = useState<string | null>(null);

  const consent = useMutation({
    mutationFn: (consent_likeness: boolean) => jsonApi("/v1/me", "PATCH", {consent_likeness}),
    onSuccess: () => qc.invalidateQueries({queryKey: ["me"]}),
  });

  const create = useMutation({
    mutationFn: () => jsonApi<Element>("/v1/elements", "POST", {type: "character", name, description: desc}),
    onSuccess: () => {
      setName("");
      setDesc("");
      qc.invalidateQueries({queryKey: ["elements"]});
    },
    onError: (e) => setNotice(String((e as Error & {detail?: unknown}).detail ?? "cannot create")),
  });

  const train = useMutation({
    mutationFn: (elementId: string) => jsonApi(`/v1/elements/${elementId}/photos`, "POST", {
      photo_asset_ids: photos.map((p) => p.id),
    }),
    onSuccess: () => qinvalidate(qc),
    onError: (e) => setNotice(String((e as Error & {detail?: unknown}).detail ?? "training rejected")),
  });

  const upload = async (files: FileList) => {
    const done: Asset[] = [];
    for (const f of Array.from(files)) {
      const res = await rawUpload("/v1/assets/upload", f, "reference");
      if (res.ok) done.push(await res.json());
    }
    setPhotos((p) => [...done, ...p]);
  };

  if (!user) return <div className="p-8 text-ink-300">Loading account…</div>;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Characters & elements</h1>
        <p className="max-w-2xl text-sm text-ink-300">
          Train one identity from 20–80 photos of a single person, then cast the same character across generations.
          Expect “clearly the same person” rather than pixel-identical faces. Only upload likenesses you&apos;re allowed to use.
        </p>
      </div>

      <Card className="space-y-4 p-5" data-testid="character-form">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Character name"><Input data-testid="char-name" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Describe the character" hint="anchor description">
            <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="noir detective, long coat, gravel voice" />
          </Field>
        </div>
        <label className="flex cursor-pointer justify-center rounded-xl border border-dashed border-ink-600 px-3 py-4 text-xs text-ink-300 hover:border-byz-400">
          upload the photo set (20–80 imgs; varied angles, good light)
          <input type="file" hidden multiple accept="image/png,image/jpeg,image/webp" onChange={(e) => e.target.files && upload(e.target.files)} />
        </label>
        <div className="flex items-center justify-between">
          <Badge tone={photos.length >= 20 ? "ok" : "neutral"}>{photos.length}/20 minimum</Badge>
          <Button data-testid="char-create" disabled={!name} onClick={() => create.mutate()}>Create character</Button>
        </div>
        {notice && <div className="rounded-lg border border-ember/40 bg-ember/10 px-3 py-2 text-xs text-ember">{notice}</div>}
        {!user.consent_likeness && (
          <button className="text-xs text-byz-300 underline" onClick={() => consent.mutate(true)}>
            I confirm likeness consent (updates preferences)
          </button>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(elements.data ?? []).map((el) => (
          <Card key={el.id} className="p-4" data-testid="character-card">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{el.name}</h3>
              <Badge tone={el.training_status === "ready" ? "ok" : el.training_status === "failed" ? "err" : "accent"}>
                {el.training_status}
              </Badge>
            </div>
            <p className="mt-1 line-clamp-2 text-xs text-ink-300">{el.description || "no description"}</p>
            <Button size="sm" variant="outline" className="mt-3" disabled={!photos.length}
              onClick={() => train.mutate(el.id)}>
              Attach photo set
            </Button>
          </Card>
        ))}
        {!elements.data?.length && (
          <EmptyState title="No characters yet" body="Create one above — trained identities unlock casting across engines." />
        )}
      </div>
    </div>
  );
}

async function qinvalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({queryKey: ["elements"]});
}
