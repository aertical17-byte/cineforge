"use client";

import {useQuery} from "@tanstack/react-query";

import {jsonApi} from "@/lib/api";
import {Badge, Card} from "@/components/ui";

type Tx = {kind: string; amount: number; source: string; description: string; created_at: string; expires_at: string | null};

export default function SettingsBilling() {
  const history = useQuery({queryKey: ["credits", "history"], queryFn: () => jsonApi<Tx[]>("/v1/credits/history", "GET")});
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold tracking-tight">Settings · Billing</h1>
      <Card className="p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-300">Credit ledger</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" data-testid="credit-table">
            <thead className="text-xs uppercase text-ink-300">
              <tr><th className="py-2">Kind</th><th className="py-2">Amount</th><th className="py-2">Source</th><th className="py-2">Description</th><th className="py-2">Expiry</th></tr>
            </thead>
            <tbody>
              {(history.data ?? []).map((t, i) => (
                <tr key={i} className="border-t border-ink-700">
                  <td className="py-2">{t.kind}</td>
                  <td className={`py-2 ${t.amount < 0 ? "text-ember" : "text-emerald-300"}`}>{t.amount > 0 ? "+" : ""}{t.amount}</td>
                  <td className="py-2"><Badge tone="neutral">{t.source}</Badge></td>
                  <td className="py-2 text-ink-200">{t.description}</td>
                  <td className="py-2 text-xs text-ink-300">{t.expires_at ? new Date(t.expires_at).toLocaleDateString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
