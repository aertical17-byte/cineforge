"use client";

import {useQuery} from "@tanstack/react-query";
import {useEffect} from "react";

import {jsonApi} from "@/lib/api";
import type {User} from "@/lib/types";
import {Button, Card, Field, Input} from "@/components/ui";

export default function SettingsProfile() {
  const me = useQuery({queryKey: ["me"], queryFn: () => jsonApi<User>("/v1/auth/me", "GET")});

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold tracking-tight">Settings · Profile</h1>
      <Card className="max-w-xl space-y-4 p-5">
        <Field label="Email"><Input value={me.data?.email ?? ""} readOnly /></Field>
        <Field label="Display name"><Input id="display-name" defaultValue={me.data?.display_name ?? ""} /></Field>
        <Button size="sm" onClick={async () => {
          const value = (document.querySelector("#display-name") as HTMLInputElement)?.value;
          await jsonApi("/v1/me", "PATCH", {display_name: value});
          me.refetch();
        }}>Save</Button>
      </Card>
      <Card className="max-w-xl space-y-2 p-5 text-sm text-ink-200">
        <h3 className="font-medium">Likeness consent</h3>
        <p className="text-xs text-ink-300">
          {me.data?.consent_likeness
            ? "Confirmed: you may upload likenesses of yourself or permitted people."
            : "Unconfirmed. Required before creating character identities."}
        </p>
      </Card>
    </div>
  );
}
