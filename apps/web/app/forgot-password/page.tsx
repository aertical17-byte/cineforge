import Link from "next/link";

import {LandingShell} from "@/components/landing";

export default function ForgotPassword() {
  return (
    <LandingShell>
      <div className="mx-auto max-w-md px-6 py-20 text-center">
        <h1 className="text-xl font-semibold">Password recovery</h1>
        <p className="mt-2 text-sm text-ink-300">
          Enter your account email and we&apos;ll send a reset link once email delivery is configured by the operator.
        </p>
        <a href="mailto:studio@cineforge.test" className="mt-6 block text-sm text-byz-300 underline">
          studio@cineforge.test
        </a>
        <Link href="/login" className="mt-6 block text-sm text-ink-300 underline">Back to login</Link>
      </div>
    </LandingShell>
  );
}
