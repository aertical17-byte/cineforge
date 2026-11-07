import {LandingShell} from "@/components/landing";

export function AuthShell({title, subtitle, children}: {title: string; subtitle: string; children: React.ReactNode}) {
  return (
    <LandingShell>
      <div className="mx-auto max-w-md px-6 py-20">
        <div className="rounded-xl2 border border-ink-700 bg-ink-850 p-7 shadow-card">
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="mt-1 mb-6 text-sm text-ink-300">{subtitle}</p>
          {children}
        </div>
      </div>
    </LandingShell>
  );
}
