# AI ENGINE — orchestration, adapters, registries

## 1. Principles (enforced in code, with honest failure paths)

1. Providers are invoked **only** in the worker via `app/providers/*` — never from the browser.
2. Missing keys raise `ProviderNotConfigured` → user-visible `provider_not_configured` + refund. **Production paths never simulate success.**
3. The mock provider is application-gated: `AI_MOCK_MODE=1` AND `ENVIRONMENT=test`. Any other environment refuses it (visible error, not an image).
4. `AIProvider` interface: `generate_image`, `generate_video`, `upscale_image`, `cancel`, `download` — implemented by `Replicate`, `Fal`, `Mock`.
5. Capability registry (`ai_models.capabilities`) governs both the UI and the request builder:
   `supports_seed / supports_negative_prompt / supports_refs / supports_camera_control / supports_first_frame / max_duration_s / aspect_ratios / max_batch / structured_params`.

## 2. Adapters (per public provider docs)

### Replicate (`providers/replicate.py`)
- `GET /v1/models/{owner}/{name}` → resolve `latest_version` at call time (no stale hashes).
- `POST /v1/predictions` with version+input (or `/v1/models/{m}/predictions` fallback), then poll `GET /v1/predictions/{id}`; outputs normalized (string | list | dict.url).
- Cancel: `POST /v1/predictions/{id}/cancel`.
- Input mapping table per model (`provider_config.input_map/fixed_input`) to adapt documented field names without code changes.

### fal.ai (`providers/fal.py`)
- Queue API: `POST https://queue.fal.run/{model_id}` → `request_id`; status `…/requests/{id}/status`; result `…/requests/{id}`; auth `Key {key}`.
- Camera control honored only when the model's registry declares `structured_params` incl. `camera` (mapping table for the documented Kling-style `{camera: {direction|effective fields}}`).
- URL extraction walker covers `images[]`, `videos[]`, url-ish keys.

### Mock (`providers/mock.py`) — tests only
- Emits obviously artificial gradient-`<svg>` "MOCK IMAGE/MOCK VIDEO" rasters; decode-through in `download()`. E2E asserts UI states, never mistaking raster for a model result (see docs/SECURITY.md §mock).

### AI Horde (`providers/aihorde.py`) — free, keyless `[V]`
- Open-source community project (github.com/Haidra-org/AI-Horde; volunteers share GPU time). Anonymous access with the well-known public key of ten zeros: no signup, no card, no quota purchase — the budget-0 generation path.
- Flow: `POST /generate/async` → `GET /generate/check/{id}` → `GET /generate/status/{id}` → image URL; anonymous tier ≈512px long side, ≈1 concurrent job per key. HTTP 429 raises `ProviderError` so the worker requeues with backoff instead of failing the job.
- Negative prompt rides the documented `prompt ### negative` separator; steps capped at 50; `r2: true` asks for direct artifact URLs (downloaded immediately by our worker, since they are short-lived).
- Images only — video requests raise `ProviderUnsupported` and the UI states it honestly. Disabled in test env so CI stays hermetic; enable with `AIHORDE_ENABLED=1` (default ON in docker compose; seed model `horde-sdxl`, 2cr/image).
- Live proof: `.github/workflows/live-smoke.yml` (manual dispatch) generates one real image with zero credentials and uploads it as an artifact.

## 3. Prompt engine (`services/prompt_engine.py`)

- `compose_prompt(prompt, film_setup, camera_move, emotion)`: renders only registry-backed fragments (genres/eras/tempo/bodies/lenses/apertures/palettes/lighting/speedramps/movesets) — original wording from `packages/shared/data/creative_registries.json`.
- `resolve_camera(caps, move)`: returns prompt fragment + structured mapping **only when the model is camera-control capable**; otherwise degrades to prompt text — never invents provider params.
- `build_{image,video}_request(model_row, …)`: clamps aspect/duration/batch to caps, drops negatives/seeds/refs the engine doesn't accept (degradation is silent, non-fatal, and *labeled in the UI*).

## 4. Editing surfaces status

| Surface | Route → Engine | Status |
| --- | --- | --- |
| Upscale image | `/create/edit` → `upscale_image` | wired; provider-dependent |
| Regional video edit | `task=edit_video` (validated/queued job path) | job pipeline ready; no adapter executes it yet → `provider_unsupported_feature` after refund |
| Video extend fwd/back | `task=extend_video` | same as above (honest) |
| Identity training | `/v1/elements/{id}/photos` | requires a trained-identity engine; keeps status `training` + explicit note until configured |

## 5. Verification hygiene

- `scripts/verify_providers.py` (CI-able, key-gated): checks Replicate auth read + fal queue reachability; writes `/logs/verify_providers.json`; UI surfaces `/v1/providers` `configured` booleans.
- Model catalog is **live DB rows** — operators can retarget provider_model/config via SQL or admin router without code deployment.
- Where an endpoint could not be verified from public docs during authoring, adapters comment the uncertainty and treat unidentified responses as `provider_error` (refund path) rather than guessing.

## 6. Cost model (credits, display = deduction)

`credit_cost_base` + `credit_cost_per_second × duration` (video), ×2 resolution premium for 4K tiers, × batch. Deterministic (`/v1/generations/preview-cost`), shown on the button, reserved identically at submit time.

## 7. Extending

Add a provider: implement `AIProvider`, add row to `ai_providers` + `ai_models` with capabilities/costs, note the docs source + verification status. No frontend change required (registry-driven UI).
