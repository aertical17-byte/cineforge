# TESTING

## What runs where (all on GitHub Actions — the build/execution environment)

| Job | Content |
| --- | --- |
| `CI · api` | Postgres+Redis sidecars → alembic upgrade (PG + SQLite) → pytest suite |
| `CI · web` | tsc typecheck → vitest (registries, primitives) → production build |
| `CI · e2e` | boots FastAPI (test env, AI_MOCK_MODE=1) + Next dev → Playwright full journey |
| `CI · docker` | builds api/worker/web images |

## API suite (`apps/api/tests`)

- `test_auth.py` — register (incl. password policy), login, bad-credential rejection, admin allowlist, welcome credits.
- `test_credits.py` — transactional spend on success, credit math (10+4×8=42 on the catalog), 402 on insolvency; mock mock-engine success path through the real worker (`process_pending`) with refund semantics available for failure; production never sees the mock (env guard).
- `test_api_flows.py` — project CRUD lifecycle, upload validation (bad MIME 415, good bytes 201), capability enforcement (bad aspect 422, plan gate 402), likeness-consent gate (403), registry exposure (camera moves).

## Web suite (`apps/web/tests`)

- `lib.test.ts` — registry invariants (20+ camera moves incl. dolly_zoom/orbit_left/crane_up/fpv; palettes; lenses), API surface sanity.
- `ui.test.tsx` — design-system primitives render with expected classes and ARIA roles (happy-dom + testing-library).

## E2E journey (`apps/e2e/journey.spec.ts`)

register → dashboard → create project → open image studio → select engine (mock) → prompt → generate → asset tile appears → library contains item → credit ledger table → history re-roll row. **Mock provider only.** Artifacts (trace/report) upload on failure.

## Idempotency & retry drills (schedule: D2 — CLI harness)

- duplicate POST with same idempotency_key returns first record (DB unique constraint).
- provider 5xx → backoff requeue ×≤3 → terminal failure → auto-refund verification (usage_log refund rows).

## Test-mode separation (hard rule)

- Mock provider requires `ENVIRONMENT=test` **and** `AI_MOCK_MODE=1`; production containers set neither.
- Assertions never treat "MOCK" raster output as a model result — e2e checks UI states (badges, tiles), not fake content semantics.
