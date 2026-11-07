"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import Link from "next/link";

import {jsonApi} from "@/lib/api";
import type {Plan} from "@/lib/types";
import {Badge, Button, Card} from "@/components/ui";

type Sub = {plan_code: string; status: string; interval: string; current_period_end: string | null};

export default function SubscriptionSettings() {
  const qc = useQueryClient();
  const plans = useQuery({queryKey: ["plans"], queryFn: () => jsonApi<Plan[]>("/v1/plans", "GET")});
  const sub = useQuery({queryKey: ["my-sub"], queryFn: () => jsonApi<Sub | null>("/v1/my/subscription", "GET")});

  const checkout = useMutation({
    mutationFn: (plan: Plan, interval: "month" | "year") =>
      jsonApi<{mode: string; message?: string; checkout_url?: string}>("/v1/billing/checkout", "POST", {
        plan_code: plan.code, interval,
      }),
    onSuccess: (data) => {
      if (data.checkout_url) {
        if (typeof window !== "undefined") window.location.assign(data.checkout_url);
      } else if (data.message) {
        document.title = "Billing not wired (readout below)";
      }
      qc.invalidateQueries({queryKey: ["my-sub"]});
    },
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings · Subscription</h1>
        <p className="text-sm text-ink-300">
          Plans unlock engines and concurrency. Operator-configured; Stripe checkout activates automatically when keys are present.
          {sub.data ? ` Current: ${sub.data.plan_code} (${sub.data.status}).` : ""}
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {(plans.data ?? []).map((p) => (
          <Card key={p.code} className={`flex flex-col p-5 ${sub.data?.plan_code === p.code ? "border-byz-500/60" : ""}`} data-testid={`plan-${p.code}`}>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-lg font-semibold">{p.name}</h3>
              {p.code === "free" && <Badge tone="neutral">starter</Badge>}
            </div>
            <div className="text-2xl font-semibold">
              {p.monthly_price_cents === 0
                ? "Free"
                : <>${(p.monthly_price_cents / 100).toFixed(0)}<span className="text-sm text-ink-300">/mo</span></>}
            </div>
            <ul className="mt-3 space-y-1.5 text-xs text-ink-200">
              <li>· {p.monthly_credits.toLocaleString()} credits / cycle</li>
              <li>· {p.max_concurrency} concurrent generation{p.max_concurrency > 1 ? "s" : ""}</li>
              {(p.features ?? []).slice(0, 3).map((f: string) => <li key={f}>· {f}</li>)}
            </ul>
            <Button size="sm" className="mt-4" disabled={p.code === "free" || sub.data?.plan_code === p.code}
              onClick={() => checkout.mutate(p, "month")} data-testid={`buy-${p.code}`}>
              {p.code === "free" ? "Included" : sub.data?.plan_code === p.code ? "Current plan" : "Choose"}
            </Button>
          </Card>
        ))}
      </div>
      <Card className="p-5 text-sm text-ink-200">
        <h3 className="mb-2 font-medium">How the credit types behave</h3>
        <ul className="list-inside list-disc space-y-1 text-xs text-ink-300">
          <li>Subscription credits reset every cycle and don&apos;t roll over.</li>
          <li>Top-up and promo credits expire; balance spends subscription lots first, then soonest expiry.</li>
          <li>Failed generations refund automatically — check the ledger under Billing.</li>
        </ul>
      </Card>
      <Link href="/settings/billing" className="text-xs text-byz-300 underline">Open credit ledger →</Link>
    </div>
  );
}
