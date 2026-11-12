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
| 2026-11-11 | CI fully green — all 4 jobs (API tests, Web build+tests, Containers, E2E journey) | ✅ done | gh run 43080950067 |
| 2026-11-11 | E2E smoke (register→project→generate(mock)→library→billing→history) | ✅ green | apps/e2e/journey.spec.ts |
| 2026-11-11 | Deployment hardening: compose validation gate in CI + `infra/deploy.sh` one-command bring-up | ✅ done | gh run 43085435903 |
| 2026-11-11 | Flowboard API (pipelines table, /v1/pipelines, stepgen shared step creation, worker chain advance, chain tests) | ✅ done | gh run 43088503651 |
| 2026-11-11 | Flowboard UI (/flowboard node-chain builder + sidebar nav) | ✅ done | gh run 43088503651 |
| 2026-11-11 | E2E chain spec (register→2-node chain→worker advances→2 assets) — all 4 jobs green | ✅ green | apps/e2e/flowboard.spec.ts, gh run 43088503651 |
| 2026-11-11 | D1.5 template deep-linking (?template= prefills studios, honest model guard) + e2e prefill spec | ✅ green | gh run 43090769392 |
| 2026-11-12 | Budget-0 real generation: AI Horde keyless provider (anonymous tier), seed model horde-sdxl, live-smoke workflow proves one REAL image (21822 bytes, job 37658ec2) with zero credentials | ✅ green | gh runs 43226687177 (smoke) + 43226656918 (ci) |
| 2026-11-12 | Repo made PUBLIC (download-friendly) + beginner-first README (Italian) + real-UI screenshot capture (`apps/e2e/shots.spec.ts` → artifact `ui-shots`) | ✅ green | gh run 43234123047 |
| 2026-11-12 | macOS installer with native UI: AppKit launcher (Italian, checks Docker, clones, compose up, polls, opens browser) + fancy dmg (dmgbuild) → release `v0.3.0` with `CineForge-AI.dmg` | ✅ published | dmg run 43237933334 |
| 2026-11-12 | Landing site published on Vercel (real screenshots labeled honestly + real AI Horde proof image + dmg mirror): https://cineforge-iota.vercel.app | ✅ live | fetch 200 on /, /guida.html, assets, mirror dmg |
| Deployment (containers compose; live cloud target) | 🟡 compose ready (self-host single command); marketing site on Vercel; app deployment stays local/docker by design | docs/DEPLOYMENT_CHECKLIST.md |
| 2026-11-12 | Sensitive parts (auth pages incl. forgot-password, admin surface, site sources) moved to a **private companion repository** (linked, same history + archive branch) — public repo keeps only what the open product serves | ✅ done | private repo created & pushed before removals |
| 2026-11-12 | **No-login mode**: `POST /v1/auth/guest` mints an ephemeral account automatically; studio gates auto-bootstrap; login/register/forgot/admin pages removed from the public product; e2e suite converted to guest flow | ✅ green | gh run 43245431549 (4 jobs) |
| 2026-11-12 | **No-limits mode**: every account (registered or guest) gets 1,000,000 welcome credits that never expire; no per-generation caps; the only real limit is the AI Horde community queue (documented honestly) | ✅ green | config + tests (insolvency path preserved via direct-lot shrink) |
| Mission Control agent, audio/lipsync execution, Flowboard depth (branch/reorder) | ⬜ backlog | docs/DEVELOPMENT_ROADMAP.md |

## Resume-from-instructions

If interrupted: (1) read the last ✅ row above; (2) check `gh run list` for the last CI state; (3) continue with the next ⬜ / 🟡 row only after CI is green.

## Honesty ledger (must stay true)

- No provider key in repo ⇒ generations that need real engines report `provider_not_configured`; **never simulated success** in production paths. Mock provider exists only under `AI_MOCK_MODE=1` (CI/test).
- All UI claims about model capabilities derive from the capability registry, not from hope.

## Debug archive (what the E2E failure taught us — do not regress)

1. `email-validator` rejects IANA special-use domains (`.test`) at parse time → e2e registers with `@example.com`.
2. `Base.metadata` must have models imported **before** `create_all` (conftest), else "no such table".
3. Shared registries resolve via `app/core/paths.py::shared_registry_path()` (cwd + ancestor walk) — fixed `parents[3]` broke between checkout/CI/Docker layouts.
4. `PresetRow` PK is composite `(id, group)` — the same id (e.g. "noir") may span registry groups.
5. `User.profile` is `lazy="selectin"` — sync FastAPI response serialization must never trigger async lazy IO.
6. SQLite returns **naive** datetimes: normalize to aware UTC before any subtraction (job timeout check, worker lease guard).
7. Provider resolution happens **inside** `run_job`'s try: `ProviderNotConfigured` → immediate `fail()` + refund, never an unhandled raise that strands a claimed job in `running` forever.
8. `Card`/`Badge` (and all primitives) must forward standard HTML props — a dropped `data-testid` makes tests select nothing while the UI looks correct.
9. Asset media URLs are app-relative `/files/…` in local storage: the web client resolves them against `API_URL` (`assetSrc`), or `<img>` would 404 against the Next.js origin.
10. GitHub Actions drops a background step's stdout once the step ends: the worker also logs to `data/worker.log`, and the e2e job dumps process census + DB inventory (`always()`).
11. Multi-process SQLite (API + worker): WAL (`pragma journal_mode=WAL`) + `connect_args timeout=30`.
12. Alembic 0001 is `metadata.create_all`: a fresh DB already contains any new model, so delta migrations (0002+) must guard every op with an inspector check (`table in get_table_names()`, column/index presence) or fresh-DB runs fail with "already exists".
13. The pytest SQLite DB is shared across ALL test files in a session: a test that intentionally leaves `queued` jobs behind (the 402-insolvency spec) consumes `process_pending(batch=N)` iterations of later tests — drain-until (poll the entity, process in rounds) instead of a single fixed batch.
14. The `ruff --select E9,F821` gate catches refactor debris immediately (renamed parameter still referenced as `user.id`): fix before pushing, it fails before tests even start.
15. AI Horde input validation (learned live): width/height must be multiples of 64 and `seed` must be a string. The live-smoke's honest gate (fail unless a real image lands) surfaced both on the first real attempt.
16. A smoke step that just exits 0 can mask a failed generation — the first live-smoke "succeeded" without producing an image (un-awaited coroutine). Verify artifacts explicitly: parse the verify JSON and assert `ok` + `bytes > 1000` in the workflow itself.
17. `python scripts/x.py` puts `scripts/` first on `sys.path`, not cwd: scripts importing the `app` package must insert `os.getcwd()` before the import.
18. GitHub's `macos-14` runner image is retired: dispatches fail with `The configuration 'macos-14-arm64-us-default' is not supported` (job cancelled in seconds, no steps logged). Use `macos-15`.
19. Runner `swiftc` rejects `-arch <a>`; use the `-target <arch>-apple-macos12.0` form per slice, then `lipo -create`.
20. `dmgbuild`/`ds_store` pack icon coordinates as **unsigned** ints: negative positions (e.g. parking `.background` at `-1000`) crash with `struct.error`. Finder hides dotfiles anyway — drop the entry.
21. `Pillow` must be installed before `make_assets.py` (runner python has no site-packages extras); install `pillow dmgbuild` in a dedicated CI step.
22. Vercel MCP deploys: `create_deployment.files` accepts only `{file, sha, size}` refs (inline `{file,data,encoding}` fails the zod union "Expected exactly one member to match") → upload bytes first via `upload_file` with a pure-JS SHA1 + base64 body. Team-scoped operations 403 until an SSO approval link (`authorize_team_access`) is clicked by the owner — link expires in 10 min, single use.
23. No-limits mode lessons: `email-validator` rejects `.local`/`.test` too (guests use `@example.com`); mixing never-expiring lots (None) with dated lots breaks naive/aware datetime sorting in sqlite → normalize in `_expiry_key`; hardcoded `== 200` balance assertions must read `settings.free_signup_credits` instead.
