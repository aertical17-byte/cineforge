# DEVELOPMENT ROADMAP

## Shipped in this milestone (v0.1)

- Research + feature inventory + UI spec + architecture + AI engine + schema + API spec + security + testing docs.
- Full API (auth, users, projects, assets/uploads+signed serving, generations + jobs pipeline, credit ledger, plans/subscriptions, Stripe-ready billing, elements/characters, registries, templates, notifications, admin, audit, rate limiting).
- Worker (lease queue, backoff, timeout, cancel, refund-on-failure, notifications).
- Web (all routes listed in docs/UI_UX_SPECIFICATION.md; design system; typed API client; live credits badge).
- CI: api (PG+Redis), web, e2e full journey, docker builds. Docker Compose deployment artifacts.

## Shipped in this milestone (v0.3 / v0.4 — public launch, no-login, no-limits)

- Public launch: repo made public; beginner-first Italian README (dmg path, free-engine expectations, honest limits).
- Real-UI proof: `apps/e2e/shots.spec.ts` captures 6 real screenshots (1440p@2x) into the `ui-shots` artifact; the marketing site shows them labeled "screenshot reale" (mock-engine tiles disclosed).
- Mac installer with UI: native AppKit launcher (Italian; Docker/git checks, auto-start Docker, folder pick, clone, `docker compose up -d --build`, health polling, opens browser, bundled offline guide) + drag-to-Applications dmg via dmgbuild (universal x86_64+arm64, ad-hoc signed); release published from CI (`v0.3.0` → refreshed as `v0.4.0`).
- Landing site on Vercel: pure static (no framework), hero/steps/real-screenshots/free-engine proof/FAQ, guide page, dmg mirror served from the site. Deployed via Vercel MCP file upload (sha/size refs).
- **No-login mode**: included engines need no credentials, so the product needs no signup — `POST /v1/auth/guest` mints an ephemeral account (no email collected, `@example.com` placeholder), the studio auto-bootstraps it, auth/admin/forgot pages removed from the public product (sources preserved in a private companion repository, same history + archive branch). E2E suite runs the guest flow.
- **No-limits mode**: 1,000,000 welcome credits for everyone (guest included), never expiring; no per-generation rate caps (auth attempt limiting stays as anti-abuse); honest framing: the only real cap is the AI Horde community queue. Credit ledger stays intact (cost display, refunds, insolvency guard) for the optional paid engines.

## Shipped in this milestone (v0.2)

- Deployment hardening: compose validation gate in CI (`docker compose config -q`), one-command `infra/deploy.sh`, checklist pointer.
- Flowboard (D3.1) end to end:
  - `pipelines` table + `/v1/pipelines` API (create/list/detail/cancel) with honest-chain rules: only step 0 exists at creation; the worker spawns each next step (jobs.finish → pipelines.advance), each step reserves its own credits, mid-chain insolvency fails the chain with a notification.
  - `services/stepgen.py`: shared step creation (validate/plan-gate/estimate/reserve) used by both `/v1/generations` and pipelines — single source of truth, no commit/enqueue inside.
  - Video step consumes the previous step's first asset as its first frame (`img2video`).
  - Web `/flowboard` node-chain builder (kind-filtered engines, per-node prompt/aspect/duration/batch, live per-step status + thumbnails, cancel, `Run chain · N credits`).
  - E2E spec `apps/e2e/flowboard.spec.ts`: register → build 2-node chain → run → both assets render; proves the separate worker process advances the chain.
- D1.5 template deep-linking: `?template=slug` prefills the studios (prompt/aspect/camera/film; engine only if actually served) + e2e `apps/e2e/template.spec.ts`.
- Budget-0 generation path: AI Horde keyless provider (`horde-sdxl`, anonymous tier — no signup, no card) enabled by default in compose; live-smoke workflow (manual dispatch) generates one real image with zero credentials and uploads it as an artifact.

## D1 — next iteration (product polish)

1. SSE/WebSocket live job stream (replace polling).
2. Gallery preview modal wiring + framer-motion transitions.
3. Settings taste: notification preferences per kind; danger-zone account deletion flow.
4. CSP + HSTS at the reverse proxy; session-cookie auth option.
5. ~~Templates deep-linking into studios (`?template=` prefill)~~ ✅ shipped (v0.2): Templates gallery links into studios; Workspace consumes the slug, prefills prompt/aspect/camera/film and selects the template's engine only when this deployment really serves it.

## D2 — operator & economy

1. Admin UI for plans/models/grants (endpoints exist today; build screens).
2. Credit-pack purchase endpoints + Stripe linked products; auto-refill thresholds.
3. Concurrency limiter enforcement line (per-plan interviews in job claim).
4. Retention purge job (hard-delete soft-deleted entities past N days).

## D3 — creative depth

1. Flowboard depth: node canvas interactions (reorder, branch, edit node type), template → chain prefill.
2. Mission Control agent (brief→plan→assets) with provider cost budgeting.
3. Audio/voiceover tools on engines offering it (registry already supports the capability bit).
4. Trained-identity engine integration (Soul-ID-style) — find an official, licensed provider/export path; keep honest consent + capability limits.

## D4 — scale

1. Multi-region storage + CDN; asset lifecycle policies.
2. Queue broker upgrade (Redis Streams) behind the same `enqueue/claim` interface.
3. Per-provider retries budgets + third-party SLA dashboards (Prometheus/Grafana).
