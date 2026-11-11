"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import Link from "next/link";
import {useState} from "react";

import {assetSrc, jsonApi} from "@/lib/api";
import {useAuthStore} from "@/lib/store";
import type {AIModel, Asset, PipelineDetail} from "@/lib/types";
import {Badge, Button, Card, Field} from "@/components/ui";

const ASPECTS = ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"];

interface FlowStep {
  kind: "image" | "video";
  model_id: string;
  prompt: string;
  aspect_ratio: string;
  duration_s: number;
  batch_size: number;
}

const freshStep = (kind: "image" | "video"): FlowStep => ({
  kind,
  model_id: "",
  prompt: "",
  aspect_ratio: kind === "image" ? "1:1" : "16:9",
  duration_s: 4,
  batch_size: 1,
});

/** Client-side mirror of the API's deterministic credit_cost (image: base × batch; video: base + per_second × s). */
function stepCost(model: AIModel | undefined, step: FlowStep): number {
  if (!model) return 0;
  if (step.kind === "image") return Math.max(1, model.credit_cost_base) * Math.max(1, step.batch_size);
  return Math.max(1, model.credit_cost_base + model.credit_cost_per_second * Math.max(1, step.duration_s));
}

export default function FlowboardPage() {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [steps, setSteps] = useState<FlowStep[]>([freshStep("image"), freshStep("video")]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const modelsQ = useQuery({queryKey: ["models"], queryFn: () => jsonApi<AIModel[]>("/v1/models", "GET")});
  const models = modelsQ.data ?? [];

  const modelsFor = (kind: "image" | "video") => models.filter((m) => m.tasks.includes(kind));

  const detailQ = useQuery({
    queryKey: ["pipeline", activeId],
    queryFn: () => jsonApi<PipelineDetail>(`/v1/pipelines/${activeId}`, "GET"),
    enabled: !!activeId,
    refetchInterval: (q: {state?: {data?: PipelineDetail}}) => {
      const st = q.state?.data?.status;
      return st && ["succeeded", "failed", "canceled"].includes(st) ? false : 2500;
    },
  });
  const detail = detailQ.data;

  const total = steps.reduce((sum, s) => sum + stepCost(models.find((m) => m.id === s.model_id), s), 0);

  const run = useMutation({
    mutationFn: async () => {
      setErr(null);
      const p = await jsonApi<PipelineDetail>("/v1/pipelines", "POST", {
        name: "Flowboard chain",
        steps: steps.map((s) => ({
          kind: s.kind, model_id: s.model_id, prompt: s.prompt,
          aspect_ratio: s.aspect_ratio,
          duration_s: s.kind === "video" ? s.duration_s : undefined,
          batch_size: s.batch_size,
        })),
      });
      setActiveId(p.id);
      void qc.invalidateQueries({queryKey: ["credits"]});
      return p;
    },
    onError: (e) => {
      const d = (e as Error & {detail?: unknown}).detail;
      setErr(typeof d === "string"
        ? d
        : (d && typeof d === "object" && "message" in d && typeof (d as {message?: unknown}).message === "string")
          ? (d as {message: string}).message
          : "chain rejected — check each node");
    },
  });

  const cancel = useMutation({
    mutationFn: async () => {
      const p = await jsonApi<PipelineDetail>(`/v1/pipelines/${activeId}/cancel`, "POST");
      void qc.invalidateQueries({queryKey: ["pipeline", activeId]});
      void qc.invalidateQueries({queryKey: ["credits"]});
      return p;
    },
  });

  const setStep = (i: number, patch: Partial<FlowStep>) =>
    setSteps((prev) => prev.map((s, j) => (j === i ? {...s, ...patch} : s)));
  const removeStep = (i: number) => setSteps((prev) => prev.filter((_, j) => j !== i));

  const running = !!activeId && ["running", "queued"].includes(detail?.status ?? "running");
  const ready = steps.length > 0 && steps.every((s) => s.prompt && s.model_id);

  if (!user) {
    return (
      <Card className="p-6 text-sm text-ink-200">
        Sign in to use Flowboard. <Link className="text-byz-300 underline" href="/login">Log in</Link>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card className="space-y-4 p-4" data-testid="flow-builder">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-ink-300">
            Chain builder · each node feeds the next
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" data-testid="flow-add-image"
              onClick={() => setSteps((p) => [...p, freshStep("image")])}>＋ image node</Button>
            <Button variant="ghost" size="sm" data-testid="flow-add-video"
              onClick={() => setSteps((p) => [...p, freshStep("video")])}>＋ video node</Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {steps.map((step, i) => (
            <NodeCard key={i} index={i} step={step} models={modelsFor(step.kind)}
              onPatch={(patch) => setStep(i, patch)} onRemove={() => removeStep(i)}
              canRemove={steps.length > 1} />
          ))}
          <div className="flex items-center justify-center rounded-xl border border-dashed border-ink-600 p-4 text-xs text-ink-300">
            next node is fed by this chain&apos;s previous output
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button data-testid="flow-run" disabled={!ready || run.isPending || running} size="lg"
            onClick={() => run.mutate()}>
            {running ? "chain running…" : run.isPending ? "submitting…" : `Run chain · ${total} credits`}
          </Button>
          {running && (
            <Button variant="ghost" onClick={() => cancel.mutate()} data-testid="flow-cancel">cancel chain</Button>
          )}
        </div>
        {err && <div className="rounded-lg border border-ember/40 bg-ember/10 px-3 py-2 text-xs text-ember" data-testid="flow-error">{err}</div>}
      </Card>

      {activeId && (
        <Card className="p-4" data-testid="flow-detail">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">Chain</span>
              <Badge tone={detail?.status === "succeeded" ? "ok" : detail?.status === "failed" ? "err"
                : detail?.status === "canceled" ? "warn" : "accent"} data-testid="flow-status">
                {detail?.status ?? "loading…"}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" onClick={() => qc.invalidateQueries()}>refresh</Button>
          </div>
          {detail?.status === "failed" && detail.error_message && (
            <p className="mb-3 text-sm text-ember" data-testid="flow-chain-error">{detail.error_message}</p>
          )}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {(detail?.steps ?? []).map((st) => (
              <StepResult key={st.index} step={st} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function NodeCard({index, step, models, onPatch, onRemove, canRemove}: {
  index: number;
  step: FlowStep;
  models: AIModel[];
  onPatch: (patch: Partial<FlowStep>) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const model = models.find((m) => m.id === step.model_id);
  const caps = model?.capabilities;
  return (
    <Card className="space-y-3 p-4" data-testid="flow-node">
      <div className="flex items-center justify-between">
        <Badge tone={step.kind === "image" ? "accent" : "neutral"}>
          {step.kind === "image" ? "🖼 image" : "🎬 video"} · step {index + 1}
        </Badge>
        {canRemove && (
          <button onClick={onRemove} aria-label={`remove step ${index + 1}`}
            className="rounded px-1.5 text-ink-300 hover:bg-ink-800 hover:text-ember">✕</button>
        )}
      </div>
      <Field label="Engine">
        <select data-testid={`flow-model-${index}`} className="w-full rounded-xl border border-ink-600 bg-ink-900 p-2.5 text-sm"
          value={step.model_id} onChange={(e) => onPatch({model_id: e.target.value})}>
          <option value="">· pick a {step.kind} engine ·</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.display_name}</option>)}
        </select>
      </Field>
      <Field label="Prompt">
        <textarea data-testid={`flow-prompt-${index}`} rows={3} maxLength={4000} value={step.prompt}
          onChange={(e) => onPatch({prompt: e.target.value})} placeholder="Describe this step…"
          className="w-full rounded-xl border border-ink-600 bg-ink-900 p-3 text-sm outline-none focus:border-byz-400" />
      </Field>
      <div className="flex flex-wrap gap-1">
        {ASPECTS.filter((a) => !caps || caps.aspect_ratios.includes(a)).map((a) => (
          <button key={a} onClick={() => onPatch({aspect_ratio: a})}
            className={`rounded-lg border px-2 py-0.5 text-xs ${step.aspect_ratio === a
              ? "border-byz-400 bg-byz-500/15 text-byz-200" : "border-ink-600 text-ink-200 hover:border-ink-500"}`}>
            {a}
          </button>
        ))}
      </div>
      {step.kind === "video" && (
        <Field label={`Duration · ${step.duration_s}s`}>
          <input type="range" min={1} max={caps?.max_duration_s || 10} value={step.duration_s}
            onChange={(e) => onPatch({duration_s: Number(e.target.value)})} className="w-full accent-[#7c5cff]" />
        </Field>
      )}
      {step.kind === "image" && (
        <Field label={`Batch · ${step.batch_size}`}>
          <input type="range" min={1} max={caps?.max_batch || 4} value={step.batch_size}
            onChange={(e) => onPatch({batch_size: Number(e.target.value)})} className="w-full accent-[#7c5cff]" />
        </Field>
      )}
    </Card>
  );
}

function StepResult({step}: {step: PipelineDetail["steps"][number]}) {
  const st = step.status;
  return (
    <div className="overflow-hidden rounded-xl border border-ink-600 bg-ink-900/60" data-testid={`flow-step-${st.index}`}>
      <div className="flex items-center justify-between px-3 py-2 text-xs">
        <span className="font-semibold">{step.kind === "image" ? "🖼" : "🎬"} step {step.index + 1}</span>
        <Badge tone={st === "succeeded" ? "ok" : st === "failed" ? "err"
          : st === "pending" ? "neutral" : "accent"}>{st}</Badge>
      </div>
      {st === "failed" && step.error_message && (
        <p className="px-3 pb-2 text-[11px] text-ember">{step.error_message}</p>
      )}
      <div className="grid grid-cols-2 gap-1 px-2 pb-2">
        {st === "pending" || st === "queued" || st === "running" ? (
          <div className="col-span-2 grid h-24 place-items-center rounded-lg border border-dashed border-ink-600 text-[11px] text-ink-300">
            {st === "pending" ? "waiting for previous step" : "generating…"}
          </div>
        ) : step.assets.map((a: Asset) => (
          <a key={a.id} href={assetSrc(a.url)} target="_blank" rel="noreferrer" data-testid="flow-node-img">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={assetSrc(a.url)} alt={`step ${step.index + 1} output`} className="h-24 w-full rounded-lg object-cover" />
          </a>
        ))}
      </div>
    </div>
  );
}
