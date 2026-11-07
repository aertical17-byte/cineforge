import Link from "next/link";

export function LandingShell({children}: {children: React.ReactNode}) {
  return (
    <div className="relative">
      <header className="sticky top-0 z-30 border-b border-ink-700/60 bg-ink-950/70 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-byz-500 text-sm font-bold text-white">CF</span>
            <span className="font-semibold tracking-tight">CineForge</span>
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            <Link href="/settings/subscription" className="hidden text-ink-200 hover:text-ink-100 sm:block">Plans</Link>
            <Link href="/login" data-testid="nav-login" className="rounded-lg px-3 py-2 text-ink-100 hover:bg-ink-800">Log in</Link>
            <Link href="/register" className="rounded-xl bg-byz-500 px-4 py-2 font-medium text-white hover:bg-byz-400">Get started</Link>
          </nav>
        </div>
      </header>
      <main className="relative">{children}</main>
    </div>
  );
}
