import Link from "next/link";
import {LandingShell} from "@/components/landing";

export default function Landing() {
  return (
    <LandingShell>
      <section className="relative overflow-hidden px-6 pb-24 pt-28 text-center sm:pt-36">
        <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-[720px] -translate-x-1/2 rounded-full bg-byz-500/25 blur-[120px]" />
        <div className="cine-noise relative mx-auto max-w-3xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-byz-500/30 bg-byz-500/10 px-3 py-1 text-xs text-byz-200">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-byz-300" /> Director-grade camera presets are live
          </div>
          <h1 className="mx-auto max-w-3xl text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl">
            Make motion pictures<br />
            <span className="bg-gradient-to-r from-byz-300 via-byz-500 to-ember bg-clip-text text-transparent">with words and a plan</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg text-ink-200">
            CineForge is an AI creative studio: generate cinematic images and video, direct the camera,
            keep characters consistent, and ship your library — one credit system, one workspace.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" data-testid="cta-start" className="rounded-xl bg-byz-500 px-6 py-3.5 text-[15px] font-medium text-white shadow-glow transition hover:bg-byz-400">
              Start free — 200 credits
            </Link>
            <Link href="/templates" className="rounded-xl border border-ink-600 px-6 py-3.5 text-[15px] text-ink-100 transition hover:border-byz-400">
              Explore templates
            </Link>
          </div>
        </div>
      </section>

      <FeatureGrid />
      <PresetsShowcase />
      <Footer />
    </LandingShell>
  );
}

function FeatureGrid() {
  const items = [
    {icon: "🎬", title: "Director's Room", body: "Genre, era, tempo, lens, aperture, palette and 22 camera moves — rendered honestly onto every engine that can honor them."},
    {icon: "🧬", title: "Elements & characters", body: "Train a character once from a photo set, then cast the same person across shots and scenes."},
    {icon: "⚙️", title: "One engine catalog", body: "Image and video engines behind one capability registry: the UI only shows what a model truly supports."},
    {icon: "🪙", title: "Transparent credits", body: "Every run shows its exact credit cost on the button before you press it. Failures refund automatically."},
    {icon: "🗂", title: "Projects & library", body: "Everything you make lands in a searchable library with settings you can re-roll."},
    {icon: "🔐", title: "Your keys, your data", body: "Self-host friendly: bring provider keys, S3-compatible storage, Postgres. No black-box lock-in."},
  ];
  return (
    <section className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-6 pb-24 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((f) => (
        <div key={f.title} className="rounded-xl2 border border-ink-700 bg-ink-850 p-6 transition hover:border-byz-500/40">
          <div className="mb-3 text-2xl">{f.icon}</div>
          <h3 className="mb-2 font-semibold">{f.title}</h3>
          <p className="text-sm leading-relaxed text-ink-200">{f.body}</p>
        </div>
      ))}
    </section>
  );
}

function PresetsShowcase() {
  const moves = ["Dolly Zoom", "Orbit Left", "Crane Up", "FPV Drone", "Tracking Shot", "Handheld", "Helicopter", "Robot Arm"];
  return (
    <section className="border-y border-ink-700 bg-ink-900/60 px-6 py-16">
      <div className="mx-auto max-w-5xl text-center">
        <h2 className="text-2xl font-semibold tracking-tight">Camera is a first-class control</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-ink-200">
          Pick a move; CineForge composes it into the prompt and, where the engine supports it, into structured camera parameters.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-2" data-testid="preset-strip">
          {moves.map((m) => (
            <span key={m} className="rounded-full border border-ink-600 bg-ink-850 px-4 py-2 text-sm text-ink-100">{m}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="mx-auto max-w-6xl px-6 pb-12 text-sm text-ink-300">
      <div className="flex flex-wrap items-center justify-between gap-6 border-t border-ink-700 pt-8">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-byz-500 text-xs font-bold text-white">CF</span>
          <span className="font-semibold text-ink-100">CineForge AI</span>
        </div>
        <nav className="flex flex-wrap gap-5">
          <Link href="/pricing-note" className="hover:text-ink-100">Pricing</Link>
          <Link href="/settings/subscription" className="hover:text-ink-100">Plans</Link>
          <a href="mailto:studio@cineforge.test" className="hover:text-ink-100">Contact</a>
        </nav>
        <span className="text-xs">Independent implementation — not affiliated with any other AI creative suite. © 2026</span>
      </div>
    </footer>
  );
}
