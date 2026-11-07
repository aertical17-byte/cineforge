"use client";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {useQueryClient} from "@tanstack/react-query";
import {useState} from "react";

import {jsonApi} from "@/lib/api";
import type {User} from "@/lib/types";
import {useAuthStore} from "@/lib/store";
import {Button, Card, Field, Input} from "@/components/ui";
import {AuthShell} from "@/components/auth-shell";

type Resp = {access_token: string; user: User};

export default function LoginPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await jsonApi<Resp>("/v1/auth/login", "POST", {email, password});
      setAuth(r.access_token, r.user);
      await qc.invalidateQueries();
      router.push("/dashboard");
    } catch (e2) {
      setErr(String((e2 as Error & {detail?: unknown}).detail ?? "login failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Log in" subtitle="Welcome back to the studio.">
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <Field label="Email"><Input data-testid="login-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Password"><Input data-testid="login-password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        {err && <div className="rounded-lg border border-ember/40 bg-ember/10 px-3 py-2 text-xs text-ember" data-testid="auth-error">{err}</div>}
        <Button data-testid="login-submit" type="submit" disabled={busy} className="w-full" size="lg">{busy ? "…" : "Log in"}</Button>
      </form>
      <div className="mt-4 flex justify-between text-xs text-ink-300">
        <Link href="/forgot-password" className="underline">Forgot password?</Link>
        <Link href="/register" className="underline">Create account</Link>
      </div>
    </AuthShell>
  );
}
