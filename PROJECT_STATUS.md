# PROJECT STATUS

Single source of truth for milestone state. Update after every meaningful step (per master plan §21) so an interrupted session can resume from here.

| Timestamp (UTC) | Step | State | Evidence |
| --- | --- | --- | --- |
| 2026-11-07 | Phase 1 research of the reference platform (public pages + live DOM) | ✅ done | docs/PRODUCT_RESEARCH.md |
| 2026-11-07 | Feature inventory & parity plan | ✅ done | docs/FEATURE_MATRIX.md |
| Repo created on GitHub (private), CI introduced | ✅ done | Actions tab |
| DB schema design + migrations | ✅ done | docs/DATABASE_SCHEMA.md + alembic 0001 |
| API implementation (auth/projects/assets/jobs/credits/billing) | ✅ done | apps/api, tests green in CI |
| Worker pipeline (lease queue, refund-on-failure) | ✅ done | apps/api/app/worker_loop.py, tests |
| Provider abstraction + adapters (replicate, fal, mock) | ✅ done | apps/api/app/providers |
| Web app (design system + all routes) | ✅ done | apps/web, build+tests on CI |
| E2E smoke (register→generate→library) | ✅ wired | .github/workflows/ci.yml (e2e job) |
| Deployment (containers compose; live cloud target) | 🟡 compose ready; cloud account needed | docs/DEPLOYMENT_CHECKLIST.md |
| Flowboard (node canvas), Mission Control agent, audio/lipsync execution | ⬜ backlog | docs/DEVELOPMENT_ROADMAP.md |

## Resume-from-instructions

If interrupted: (1) read the last ✅ row above; (2) check `gh run list` for the last CI state; (3) continue with the next ⬜ / 🟡 row only after CI is green.

## Honesty ledger (must stay true)

- No provider key in repo ⇒ generations that need real engines report `provider_not_configured`; **never simulated success** in production paths. Mock provider exists only under `AI_MOCK_MODE=1` (CI/test).
- All UI claims about model capabilities derive from the capability registry, not from hope.
