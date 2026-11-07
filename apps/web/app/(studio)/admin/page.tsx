"use client";

import Link from "next/link";

import {Card} from "@/components/ui";
import {useAuthStore} from "@/lib/store";

export default function Admin() {
  const user = useAuthStore((s) => s.user);
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Admin control</h1>
        <p className="text-sm text-ink-300">Operator surface: provider status, plan pricing, credit grants.</p>
      </div>
      {!user?.is_admin ? (
        <Card className="p-6 text-sm text-ink-200">Admin-only area. Configure ADMIN_EMAILS on the deployment to bootstrap operator accounts.</Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="p-5">
            <h3 className="font-medium">Provider configuration</h3>
            <p className="mt-1 text-xs text-ink-300">
              The API validates provider keys at runtime. Operators set REPLICATE_API_TOKEN / FAL_KEY in the environment;
              the status endpoint reports configured state honestly (see <code className="text-byz-300">/v1/providers</code>).
            </p>
          </Card>
          <Card className="p-5">
            <h3 className="font-medium">Pricing & grants</h3>
            <p className="mt-1 text-xs text-ink-300">
              Plans are DB rows (admin API <code className="text-byz-300">/v1/admin/plans</code>); grants go through
              <code className="text-byz-300"> /v1/admin/credits/grant</code>. Wire these into the UI in the next milestone.
            </p>
          </Card>
        </div>
      )}
      <Link href="/dashboard" className="text-xs text-byz-300 underline">← dashboard</Link>
    </div>
  );
}
