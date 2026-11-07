# DEVELOPMENT ROADMAP

## Shipped in this milestone (v0.1)

- Research + feature inventory + UI spec + architecture + AI engine + schema + API spec + security + testing docs.
- Full API (auth, users, projects, assets/uploads+signed serving, generations + jobs pipeline, credit ledger, plans/subscriptions, Stripe-ready billing, elements/characters, registries, templates, notifications, admin, audit, rate limiting).
- Worker (lease queue, backoff, timeout, cancel, refund-on-failure, notifications).
- Web (all routes listed in docs/UI_UX_SPECIFICATION.md; design system; typed API client; live credits badge).
- CI: api (PG+Redis), web, e2e full journey, docker builds. Docker Compose deployment artifacts.

## D1 — next iteration (product polish)

1. SSE/WebSocket live job stream (replace polling).
2. Gallery preview modal wiring + framer-motion transitions.
3. Settings taste: notification preferences per kind; danger-zone account deletion flow.
4. CSP + HSTS at the reverse proxy; session-cookie auth option.
5. Templates deep-linking into studios (`?template=` prefill) — route param consumer.

## D2 — operator & economy

1. Admin UI for plans/models/grants (endpoints exist today; build screens).
2. Credit-pack purchase endpoints + Stripe linked products; auto-refill thresholds.
3. Concurrency limiter enforcement line (per-plan interviews in job claim).
4. Retention purge job (hard-delete soft-deleted entities past N days).

## D3 — creative depth

1. Flowboard node canvas (image→video→edit chains) — the reference "Canvas" equivalent surface.
2. Mission Control agent (brief→plan→assets) with provider cost budgeting.
3. Audio/voiceover tools on engines offering it (registry already supports the capability bit).
4. Trained-identity engine integration (Soul-ID-style) — find an official, licensed provider/export path; keep honest consent + capability limits.

## D4 — scale

1. Multi-region storage + CDN; asset lifecycle policies.
2. Queue broker upgrade (Redis Streams) behind the same `enqueue/claim` interface.
3. Per-provider retries budgets + third-party SLA dashboards (Prometheus/Grafana).
