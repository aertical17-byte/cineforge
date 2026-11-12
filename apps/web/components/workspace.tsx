"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import Link from "next/link";
import {useSearchParams} from "next/navigation";
import {useEffect, useMemo, useState} from "react";

import {assetSrc, jsonApi, rawUpload} from "@/lib/api";
import {cameraMoves, names} from "@/lib/registries";
import {useAuthStore} from "@/lib/store";
import type {AIModel, Asset, GenerationDetail, Project, Template} from "@/lib/types";
import {Badge, Button, Card, Field, Input, Skeleton, Tabs} from "@/components/ui";

interface FilmSetup {
  genre?: string; era?: string; tempo?: string; camera_body?: string; lens?: string;
  aperture?: string; palette?: string; lighting?: string; speed_ramp?: string; moveset_style?: string;
}

const ASPECTS = ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"];

type Mode = "t2x" | "i2x";

/** The unified creation surface. type: "image" | "video" | "edit" */
export function Workspace({type}: {type: "image" | "video" | "edit"}) {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [prompt, setPrompt] = useState("");
  const [negative, setNegative] = useState("");
  const [modelId, setModelId] = useState("");
  const [aspect, setAspect] = useState("16:9");
  const [duration, setDuration] = useState(5);
  const [batch, setBatch] = useState(2);
  const [seed, setSeed] = useState<number | "">("");
  const [camera, setCamera] = useState("");
  const [film, setFilm] = useState<FilmSetup>({});
  const [refs, setRefs] = useState<Asset[]>([]);
  const [projectId, setProjectId] = useState("");
  const [activeGen, setActiveGen] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>(type === "video" ? "t2x" : "t2x");
  const [templateName, setTemplateName] = useState<string | null>(null);

  const modelsQ = useQuery({queryKey: ["models"], queryFn: () => jsonApi<AIModel[]>("/v1/models", "GET")});
  const projectsQ = useQuery({
    queryKey: ["projects"],
    queryFn: () => jsonApi<Project[]>("/v1/projects", "GET"),
    enabled: !!user,
  });

  // Deep-linked template (?template=slug from the Templates gallery): prefill once,
  // honestly — only fields the template actually carries, and the model only if this
  // deployment really serves it for the active task.
  const params = useSearchParams();
  const templateSlug = params.get("template");
  const templatesQ = useQuery({
    queryKey: ["templates"],
    queryFn: () => jsonApi<Template[]>("/v1/templates", "GET"),
    enabled: !!templateSlug,
  });
  const [prefilledSlug, setPrefilledSlug] = useState<string | null>(null);
  const detailQ = useQuery({
    queryKey: ["generation", activeGen],
    queryFn: () => jsonApi<GenerationDetail>(`/v1/generations/${activeGen}`, "GET"),
    enabled: !!activeGen,
    refetchInterval: (q: {state?: {data?: GenerationDetail}}) => {
      const st = q.state?.data?.status;
      return st && ["succeeded", "failed", "canceled"].includes(st) ? false : 2500;
    },
  });

  const wantsMediaType: "image" | "video" = type === "video" ? "video" : "image";
  const taskChoices = useMemo(() => {
    if (type === "image") return [{task: "text2img", media_type: "image" as const, label: "Text → Image"}];
    if (type === "video") return [
      {task: "text2video", media_type: "video" as const, label: "Text → Video"},
      {task: "img2video", media_type: "video" as const, label: "Image → Video"},
    ];
    return [
      {task: "upscale", media_type: "image" as const, label: "Enhance / Upscale"},
      {task: "edit_video", media_type: "video" as const, label: "Video edit"},
    ];
  }, [type]);
  const activeTask = taskChoices[type === "video" && mode === "i2x" ? 1 : 0];

  // Deep-linked template (?template=slug from the Templates gallery): prefill once,
  // honestly — only fields the template actually carries, and the model only if this
  // deployment really serves it for the active task.
  useEffect(() => {
    if (!templateSlug || prefilledSlug === templateSlug || !templatesQ.data || !modelsQ.data) return;
    const tpl = templatesQ.data.find((t) => t.slug === templateSlug);
    if (!tpl) return;
    setPrefilledSlug(templateSlug);
    setTemplateName(tpl.name);
    setPrompt(tpl.prompt);
    const st = tpl.settings || {};
    if (st.aspect_ratio) setAspect(st.aspect_ratio);
    if (type === "video" && st.camera_move) setCamera(st.camera_move);
    if (st.film_setup) setFilm((f) => ({...f, ...st.film_setup}));
    const wanted = modelsQ.data.find((m) => m.id === st.model_id && m.tasks.includes(activeTask.media_type));
    if (wanted) setModelId(wanted.id);
  }, [templateSlug, templatesQ.data, modelsQ.data, prefilledSlug, activeTask.media_type, type]);

  const compatible = useMemo(
    () => (modelsQ.data ?? []).filter((m) => m.tasks.includes(activeTask.media_type)),
    [modelsQ.data, activeTask],
  );

  useEffect(() => {
    if (!modelId && compatible.length > 0) setModelId(compatible[0].id);
  }, [compatible, modelId]);
  useEffect(() => {
    if (modelId && compatible.length && !compatible.some((m) => m.id === modelId)) {
      setModelId(compatible[0].id);
    }
  }, [activeTask, compatible, modelId]);

  const model = compatible.find((m) => m.id === modelId);
  const caps = model?.capabilities;
  const estimate = model
    ? Math.max(1, (activeTask.media_type === "video"
        ? model.credit_cost_base + model.credit_cost_per_second * duration
        : model.credit_cost_base)) * batch
    : null;

  const submit = useMutation({
    mutationFn: async () => {
      setErr(null);
      const refIds = (caps?.supports_refs ? refs.slice(0, 50).map((a) => a.id) : []);
      const rerollSeed = seed === "" ? undefined : Number(seed);
      const body = {
        media_type: activeTask.media_type,
        task: activeTask.task,
        model_id: modelId,
        prompt,
        negative_prompt: caps?.supports_negative_prompt ? negative : "",
        project_id: projectId || null,
        batch_size: activeTask.media_type === "image" ? batch : 1,
        aspect_ratio: aspect,
        duration_s: activeTask.media_type === "video" ? duration : undefined,
        seed: rerollSeed,
        camera_move: activeTask.media_type === "video" ? camera : undefined,
        film_setup: activeTask.media_type === "video"
          ? film
          : {palette: film.palette, lighting: film.lighting},
        reference_asset_ids: refIds,
      };
      const g = await jsonApi<GenerationDetail>("/v1/generations", "POST", body);
      setActiveGen(g.id);
      void qc.invalidateQueries({queryKey: ["history"]});
      void qc.invalidateQueries({queryKey: ["credits"]});
      return g;
    },
    onError: (e) => {
      const d = (e as Error & {detail?: unknown}).detail;
      setErr(typeof d === "string"
        ? d
        : (d && typeof d === "object" && "message" in d && typeof (d as {message?: unknown}).message === "string")
          ? (d as {message: string}).message
          : "generation rejected — check the form");
    },
  });

  const upload = async (files: FileList) => {
    const created: Asset[] = [];
    for (const f of Array.from(files)) {
      const res = await rawUpload("/v1/assets/upload", f, "reference");
      if (res.ok) created.push((await res.json()) as Asset);
    }
    setRefs((r) => [...created, ...r].slice(0, 50));
  };

  if (!user) {
    return (
      <Card className="p-6 text-sm text-ink-200">
        Preparing your guest session — the studio opens automatically in a moment.
      </Card>
    );
  }

  const showCamera = type === "video";
  const busy = submit.isPending || (!!activeGen && ["queued", "running"].includes(detailQ.data?.status ?? "queued"));

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[380px_1fr]">
      {/* controls column */}
      <div className="space-y-4">
        <Card className="space-y-4 p-4">
          {templateName && (
            <div className="flex items-center gap-2 text-xs text-ink-300" data-testid="template-applied">
              <Badge tone="accent">template</Badge> {templateName}
            </div>
          )}
          {taskChoices.length > 1 && (
            <Tabs items={taskChoices.map((t, i) => ({id: String(i), label: t.label}))}
              active={type === "video" && mode === "i2x" ? "1" : "0"}
              onChange={(v) => setMode(v === "1" ? "i2x" : "t2x")} />
          )}
          <Field label={activeTask.task === "img2video" ? "Scene description (moves the frame)" : "Prompt"} hint={`${prompt.length}/4000`}>
            <textarea
              data-testid="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={type === "video" ? 5 : 4}
              maxLength={4000}
              placeholder={activeTask.task === "img2video"
                ? "Upload a first frame below, describe how it should move…"
                : "Describe the shot…"}
              className="w-full rounded-xl border border-ink-600 bg-ink-900 p-3 text-sm outline-none focus:border-byz-400"
            />
          </Field>
          {caps?.supports_negative_prompt && (
            <Field label="Negative prompt">
              <Input data-testid="negative" value={negative} onChange={(e) => setNegative(e.target.value)} placeholder="what to avoid" />
            </Field>
          )}
          <Button data-testid="generate" disabled={!prompt || submit.isPending || !modelId}
            onClick={() => submit.mutate()} className="w-full" size="lg">
            {submit.isPending ? "submitting…" : `Generate · ${estimate ?? "–"} credits`}
          </Button>
          {err && <div className="rounded-lg border border-ember/40 bg-ember/10 px-3 py-2 text-xs text-ember" data-testid="gen-error">{err}</div>}
          {caps && (
            <div className="flex flex-wrap gap-1.5">
              <Badge tone={caps.supports_seed ? "accent" : "neutral"}>seed {caps.supports_seed ? "on" : "n/a"}</Badge>
              <Badge tone={caps.supports_refs ? "accent" : "neutral"}>references</Badge>
              {showCamera && (
                <Badge tone={caps.supports_camera_control ? "accent" : "neutral"}>
                  camera {caps.supports_camera_control ? "structured" : "→ prompt text"}
                </Badge>
              )}
              {showCamera && <Badge tone="neutral">max {caps.max_duration_s}s</Badge>}
            </div>
          )}
        </Card>

        <Card className="space-y-3 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-ink-300">Engine</div>
          <select data-testid="model-select" className="w-full rounded-xl border border-ink-600 bg-ink-900 p-2.5 text-sm"
            value={modelId} onChange={(e) => setModelId(e.target.value)}>
            {compatible.map((m) => (
              <option key={m.id} value={m.id}>{m.display_name}</option>
            ))}
          </select>
          <div className="flex flex-wrap gap-1">
            {ASPECTS.filter((a) => !caps || caps.aspect_ratios.includes(a)).map((a) => (
              <button key={a} data-testid={`aspect-${a}`} onClick={() => setAspect(a)}
                className={`rounded-lg border px-2.5 py-1 text-xs ${aspect === a ? "border-byz-400 bg-byz-500/15 text-byz-200" : "border-ink-600 text-ink-200 hover:border-ink-500"}`}>
                {a}
              </button>
            ))}
          </div>
          {wantsMediaType === "video" ? (
            <Field label={`Duration · ${duration}s`}>
              <input data-testid="duration" type="range" min={1} max={caps?.max_duration_s || 10} value={duration}
                onChange={(e) => setDuration(Number(e.target.value))} className="w-full accent-[#7c5cff]" />
            </Field>
          ) : null}
          {activeTask.media_type === "image" && (
            <Field label={`Batch · ${batch}`}>
              <input type="range" min={1} max={caps?.max_batch || 4} value={batch}
                onChange={(e) => setBatch(Number(e.target.value))} className="w-full accent-[#7c5cff]" />
            </Field>
          )}
          {caps?.supports_seed && (
            <Field label="Seed (optional)">
              <Input data-testid="seed" type="number" value={seed as unknown as string}
                onChange={(e) => setSeed(e.target.value === "" ? "" : Number(e.target.value))} placeholder="random" />
            </Field>
          )}
          <Field label="Project">
            <select data-testid="project-select" className="w-full rounded-xl border border-ink-600 bg-ink-900 p-2.5 text-sm"
              value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">· no project ·</option>
              {(projectsQ.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
        </Card>

        <Card className="space-y-3 p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-300">References</div>
            <Badge tone={refs.length > 0 && !caps?.supports_refs ? "warn" : "neutral"}>
              {caps?.supports_refs ? "model honors refs" : "model ignores refs"}
            </Badge>
          </div>
          <label className="block cursor-pointer rounded-xl border border-dashed border-ink-600 px-3 py-4 text-center text-xs text-ink-300 hover:border-byz-400" data-testid="ref-upload">
            upload png/jpg/webp (≤32MB)
            <input type="file" multiple accept="image/png,image/jpeg,image/webp" hidden
              onChange={(e) => e.target.files && upload(e.target.files)} />
          </label>
          <div className="grid grid-cols-4 gap-2">
            {refs.map((r) => (
              <div key={r.id} className="group relative overflow-hidden rounded-lg border border-ink-600">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={assetSrc(r.url)} alt="reference" className="h-16 w-full object-cover" />
                <button className="absolute right-1 top-1 hidden rounded bg-black/70 px-1 text-[10px] group-hover:block"
                  onClick={() => setRefs((prev) => prev.filter((x) => x.id !== r.id))}>✕</button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* right column */}
      <div className="space-y-5">
        {showCamera && (
          <Card className="p-4" data-testid="camera-panel">
            <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-300">Camera move</div>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
              {cameraMoves().map((c) => (
                <button key={c.id} data-testid={`cam-${c.id}`} title={c.fragment}
                  onClick={() => setCamera(camera === c.id ? "" : c.id)}
                  className={`rounded-xl border p-2 text-[11px] leading-tight transition ${camera === c.id ? "border-byz-400 bg-byz-500/15 text-byz-200" : "border-ink-600 bg-ink-900 text-ink-200 hover:border-ink-500"}`}>
                  {c.name}
                </button>
              ))}
            </div>
            <details className="mt-3" open>
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-ink-300">Film setup</summary>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                <SetupSelect label="Genre" group="genres" value={film.genre} on={(v) => setFilm((f) => ({...f, genre: v}))} />
                <SetupSelect label="Era" group="eras" value={film.era} on={(v) => setFilm((f) => ({...f, era: v}))} />
                <SetupSelect label="Tempo" group="tempo" value={film.tempo} on={(v) => setFilm((f) => ({...f, tempo: v}))} />
                <SetupSelect label="Camera" group="camera_bodies" value={film.camera_body} on={(v) => setFilm((f) => ({...f, camera_body: v}))} />
                <SetupSelect label="Lens" group="lenses" value={film.lens} on={(v) => setFilm((f) => ({...f, lens: v}))} />
                <SetupSelect label="Aperture" group="apertures" value={film.aperture} on={(v) => setFilm((f) => ({...f, aperture: v}))} />
                <SetupSelect label="Palette" group="palettes" value={film.palette} on={(v) => setFilm((f) => ({...f, palette: v}))} />
                <SetupSelect label="Lighting" group="lighting_presets" value={film.lighting} on={(v) => setFilm((f) => ({...f, lighting: v}))} />
                <SetupSelect label="Speed ramp" group="speed_ramps" value={film.speed_ramp} on={(v) => setFilm((f) => ({...f, speed_ramp: v}))} />
                <SetupSelect label="Move style" group="moveset_styles" value={film.moveset_style} on={(v) => setFilm((f) => ({...f, moveset_style: v}))} />
              </div>
            </details>
          </Card>
        )}

        <ResultsPanel detail={detailQ.data} active={activeGen}/>

        <Card className="flex items-center justify-between p-4 text-sm text-ink-200">
          <span>Results appear in <Link className="text-byz-300 underline" href="/library">Library</Link></span>
          <Button variant="ghost" size="sm" onClick={() => qc.invalidateQueries()}>refresh</Button>
        </Card>
      </div>
    </div>
  );
}

function SetupSelect({label, group, value, on}: {label: string; group: string; value?: string; on: (v: string | undefined) => void}) {
  const rows = names(group);
  return (
    <Field label={label}>
      <select className="w-full rounded-lg border border-ink-600 bg-ink-900 p-2 text-xs"
        value={value ?? ""} onChange={(e) => on(e.target.value || undefined)}>
        <option value="">·</option>
        {rows.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
      </select>
    </Field>
  );
}

function ResultsPanel({detail, active}: {detail?: GenerationDetail; active: string | null}) {
  if (!active || !detail) {
    return (
      <Card className="flex min-h-40 items-center justify-center p-6 text-sm text-ink-300">
        Submit a generation to see results here.
      </Card>
    );
  }
  const st = detail.status;
  return (
    <Card className="p-4" data-testid="results">
      <div className="mb-3 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          {st === "succeeded" && <Badge tone="ok">ready</Badge>}
          {st === "failed" && <Badge tone="err">failed</Badge>}
          {st === "canceled" && <Badge tone="warn">canceled</Badge>}
          {(st === "queued" || st === "running") && <Badge tone="accent">{st}…</Badge>}
        </div>
        {st === "failed" && (
          <span className="text-xs text-ink-300" data-testid="fail-note">
            {detail.error_code} — credits refunded automatically
          </span>
        )}
      </div>
      {st === "failed" ? (
        <p className="text-sm text-ink-200">{detail.error_message}</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {["queued", "running"].includes(st)
            ? Array.from({length: Math.max(1, detail.batch_size)}).map((_, i) => <Skeleton key={i} className="aspect-video" />)
            : detail.assets.map((a) => (
              <div key={a.id} className="overflow-hidden rounded-xl border border-ink-600">
                {a.kind === "video" ? (
                  <video src={assetSrc(a.url)} controls className="w-full" />
                ) : (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={assetSrc(a.url)} alt="generation result" className="w-full cursor-zoom-in" />
                )}
                <div className="flex justify-between p-2 text-[11px] text-ink-300">
                  <a href={assetSrc(a.url)} download target="_blank" rel="noreferrer" className="underline">download</a>
                  <span>{new Date(a.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
        </div>
      )}
    </Card>
  );
}
