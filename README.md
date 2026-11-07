# CineForge AI

An independent, production-oriented **AI creative platform** (image + video generation, cinematography presets, character references, credits, subscriptions, media library) — architected as a professional SaaS and **built, tested and delivered entirely on GitHub Actions**.

> This is an original implementation inspired by the *publicly observable functionality* of higgsfield.ai. It is not affiliated with, endorsed by, or copying assets/code/marketing text from that site. See `docs/PRODUCT_RESEARCH.md` for the ethics and evidence rules.

## What is implemented (MVP, real code — links in `PROJECT_STATUS.md`)

- **Web app** (`apps/web`, Next.js 14 + TS + Tailwind + Zustand + React Query): landing, auth, dashboard, generation workspace (image/video), tools, projects, library, history, templates, presets, characters, settings (profile/billing/subscription), admin.
- **API** (`apps/api`, FastAPI + SQLAlchemy 2 async): JWT auth, projects, assets/uploads, generation jobs, credit ledger (5 credit kinds, spend order, auto-refund), plan & model catalog, characters/elements, camera/film preset registries, rate limiting, audit logs, Stripe-ready billing, provider abstraction (Replicate + fal.adapters + test-only mock).
- **Worker** (`apps/worker`): async job runner — lease-based queue, retries with backoff, timeouts, cancellation, refund-on-failure, asset import + thumbnailing.
- **DB**: Postgres (SQLAlchemy models + Alembic migrations; SQLite driver available for CI/dev).
- **Storage**: S3-compatible (boto3) **or** local disk + signed URLs (dev/CI default).
- **Docs**: `docs/*.md` (research, feature matrix, UI/UX spec, architecture, AI engine, DB schema, API spec, security, testing, roadmap, deployment checklist, cost model).
- **CI**: `.github/workflows/ci.yml` — API tests on Postgres+Redis services, migration check, web typecheck/build/test, Docker builds, end-to-end smoke (register → project → generate with the test mock → library → credits), all running **on GitHub Actions**.

## Run it

Locally (optional): see `Makefile` (`make api`, `make web`, `make worker`) and `infra/docker/docker-compose.yml`.
On CI (default, nothing on a local machine): every push runs the full pipeline; artifacts and job logs under the *Actions* tab.

```bash
gh repo view aertical17-byte/cineforge --web   # then: Actions tab
```

## Status

Authoritative live state: `PROJECT_STATUS.md`. Completed/partial/key-required feature lists: `docs/FEATURE_MATRIX.md`.
