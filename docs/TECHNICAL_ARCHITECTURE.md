# TECHNICAL ARCHITECTURE — CineForge AI

Stack decision record + system map.

## 1. Stack (chosen)

| Layer | Choice | Why |
| --- | --- | --- |
| Web | Next.js 14 App Router, TS, Tailwind, Zustand, React Query, Framer Motion | SSR marketing + client workspace; typed boundary |
| API | FastAPI (async) | Providers/jobs are IO-bound; Python has the widest AI-SDK reach |
| ORM/DB | SQLAlchemy 2 async + Alembic; PostgreSQL (prod), SQLite (CI/dev) | transactional credits need SELECT/FOR UPDATE on PG |
| Worker | python loop w/ lease queue (`SELECT … FOR UPDATE SKIP LOCKED`) | zero infra beyond DB; Redis optional |
| Storage | S3-compatible (boto3) **or** local-disk + HMAC-signed URLs (dev/CI) | same interface both modes |
| Payments | Stripe (optional) | tokenized, webhooks; admin-managed fallback mode |
| CI | GitHub Actions (this is the primary execution environment) | per requirement: nothing runs locally |

Deliberate deviation from the suggested monorepo `packages/ui`: the web app is self-contained (`apps/web/components`) to keep one build toolchain; shared *data* (creative registries) lives in `packages/shared/data/creative_registries.json` and is consumed by both Python and TS from the single source file.

## 2. System map

```
 Browser ──(JWT)──► FastAPI API ──► Postgres (data + job queue)
                        │  ▲             ▲
                        │  └── assets ───┤
                        ▼                │
                    Storage (S3/local)   │
 Worker(s) ──claim jobs (lease) ──────────┘
    │
    ├─► provider.execute() (Replicate / fal / "mock" test-only)
    ├─► storage.put()
    └─► refund-on-failure / notifications
```

- API never calls providers synchronously for heavy work; `/v1/generations` reserves credits in the same transaction that it enqueues a `generation_jobs` row (atomicity ⇒ refund honesty).
- Worker claims via lease; retry with exponential backoff (≤3 attempts); timeout 20 min; lease staleness re-queues hung jobs.
- Frontend polls `/v1/generations/{id}` (2.5s while queued/running); SSE upgrade is on the roadmap.

## 3. Credit economy (implementable invariants)

- Lots: `subscription | pack | auto_refill | promo | boost | refund`.
- Spend order at execution time: **subscription first**, then **soonest expiry** — enforced by SQL ordering inside the deduction query.
- `reserve_for_generation()` runs inside the same DB transaction as the `generations` insert; over-draw impossible (`InsufficientCredits` → HTTP 402).
- Failure/cancel ⇒ automatic `refund` lot (90d expiry), usage-log row, notification.

## 4. Job lifecycle (matches master-plan Phase 8)

1. POST /v1/generations (validated: capabilities, plan gate, idempotency) → 201 + `queued`.
2. Worker claims (lease) → `running` → provider call → artifacts downloaded → `/assets` rows → `succeeded`.
3. Provider failure → retry/backoff → terminal `failed` → **auto refund** + notification.
4. Cancellation anytime before provider result → refund; provider cancel when API offers it.
5. Every transition auditable via `usage_logs`, `audit_logs`, `notifications`.

## 5. Security architecture

- JWT (HS256, issuer-checked, 14d) or API keys (SHA-256 digest storage, prefix lookup); no cookies for SPA by design (CSRF surface avoided) — document for session-cookie upgrade.
- Rate limiting: auth endpoints 20/min/IP; general API 120/min. DB-backed rolling windows in MVP; Redis drop-in when `REDIS_URL` set.
- Uploads: magic-byte sniffed (png/jpeg/webp), ≤32MB, MIME whitelist, x-content-type-options, path-traversal-proof local file serving (signed URLs with TTL).
- Provider keys never shipped to client; `/v1/providers` exposes only boolean `configured`.
- Full security notes: docs/SECURITY.md.

## 6. Environments

| Env | DATABASE_URL | AI providers | Notes |
| --- | --- | --- | --- |
| CI (GH Actions) | Postgres service + sqlite | mock only | mock provider forbidden outside `ENVIRONMENT=test` |
| Dev | sqlite local | any configured keys allowed via env | uvicorn + worker + next dev |
| Prod (compose) | Postgres | env keys | non-root containers, cap_drop, no-new-privileges |

## 7. Known trade-offs (honesty ledger)

1. **In-process polling** between web↔API; SSE/WebSocket upgrade planned (roadmap D1).
2. **Direct SQLite dev DB** instead of dockerized PG — prod parity preserved by CI running tests on real Postgres.
3. **Registry seeding** writes model knowledge captured at authoring time; `scripts/verify_providers.py` is the operator's live-check; model configs are editable rows, not code-frozen.
4. Stripe checkout session constructs minimal line items (`price` env) — requires operator to provide real Price IDs (documented deployment step).
