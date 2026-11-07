"use client";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {useState} from "react";

import {jsonApi} from "@/lib/api";
import {useAuthStore} from "@/lib/store";
import type {User} from "@/lib/types";
import {Button, Field, Input} from "@/components/ui";
import {AuthShell} from "@/components/auth-shell";

type Resp = {access_token: string; user: User};

export default function RegisterPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await jsonApi<Resp>("/v1/auth/register", "POST", {
        email, password, display_name: name, consent_likeness: consent,
      });
      setAuth(r.access_token, r.user);
      router.push("/dashboard");
    } catch (e2) {
      const d = (e2 as Error & {detail?: unknown}).detail;
      const msg = Array.isArray(d) ? d.map((x: {msg?: string}) => x.msg ?? "").join("; ") : String(d ?? "registration failed");
      setErr(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Create your studio" subtitle="200 welcome credits on the house — engines are configured by the operator.">
      <form onSubmit={submit} className="space-y-4" data-testid="register-form">
        <Field label="Display name"><Input data-testid="reg-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Alex Director" /></Field>
        <Field label="Email"><Input data-testid="reg-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Password" hint="10+ chars, 1 digit, 1 uppercase">
          <Input data-testid="reg-password" type="password" required minLength={10} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <label className="flex gap-2 text-xs text-ink-200">
          <input data-testid="reg-consent" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
          <span>I will only upload photos of myself or of people who permitted their likeness.</span>
        </label>
        {err && <div className="rounded-lg border border-ember/40 bg-ember/10 px-3 py-2 text-xs text-ember" data-testid="auth-error">{err}</div>}
        <Button data-testid="reg-submit" type="submit" disabled={busy} className="w-full" size="lg">{busy ? "…" : "Create account"}</Button>
      </form>
      <div className="mt-4 text-center text-xs text-ink-300">
        Already a member? <Link href="/login" className="underline">Log in</Link>
      </div>
    </AuthShell>
  );
}
