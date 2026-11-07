# FEATURE MATRIX — reference capability vs CineForge implementation status

Verification basis: public reference-site evidence (`[V]`), extrapolation (`[H]`), our own extension (`[P]`).
Status legend: ✅ implemented and tested · 🟡 partial (works, smaller surface) · 🔧 wired end-to-end, needs API key to actually run · 🧪 UI complete, backend accepts and validates but no provider executes it yet · ⬜ next milestone (design present, not built).

## A. Platform core

| Capability | Reference evidence | Status |
| --- | --- | --- |
| Public landing with launch sections + community gallery | V | ✅ |
| Email register / login / forgot-password / sessions (JWT) | V (auth surface exists) | ✅ |
| Profile, settings, notifications | V | ✅ profile+settings · 🟡 notifications preferences |
| Projects (create/rename/delete/archive) | V (workspace model) | ✅ |
| Media library (search/filter/preview/download/delete) | V | ✅ |
| Generation history + "duplicate settings" of a past generation | V | ✅ |
| Upload gallery (images); MIME/size validation | V (reference picker) | ✅ |
| Search, filter, pagination/infinite scroll | V | 🟡 (media type + date + text filter; infinite scroll) |
| Admin surface (plans, models, credit grants, users) | H | ✅ minimal admin`

## B. Generation engines

| Capability | Reference evidence | Status |
| --- | --- | --- |
| Text→image (families: signature-cinematic / fast-reference / text-accurate / reasoning / speed) | V | 🔧 adapters for Replicate + fal, catalog seeded; keyless deployments see explicit "provider not configured" |
| Image→image with reference strength | V | 🟡 strength passed when provider supports it |
| Batch generations (N per call) | V (grid outputs) | ✅ |
| Seed, negative prompt where supported | V | ✅ capability-registry-gated |
| Text→video | V | 🔧 (Replicate/fal engines; keyless honest error) |
| Image→video (first frame) | V | 🔧 |
| First+last frame control | V (engine listed) | 🟡 fal engine adapter flags capability |
| Video→video regional edit | V (4.0 "Edit Video") | 🧪 backend validates+queues, provider marked experimental |
| Video extend forward/backward | V | 🧪 |
| Upscale/enhance image | V | 🔧 provider adapter present |
| Voiceover/lipsync | V | ⬜ (models catalogued, no execution path yet) |

## C. Direction & cinematography

| Capability | Reference evidence | Status |
| --- | --- | --- |
| Camera move presets (dolly, orbit, pan, tilt, crane, tracking, FPV, handheld, static, drone, dolly-zoom, zoom in/out, POV, robot arm, helicopter) | V | ✅ preset registry (20 moves) rendered into prompts + provider params where supported |
| Genre set (7) + film era + tempo/cut-speed | V | ✅ FilmSetup controls |
| Lens / aperture / camera-body pickers | V | ✅ |
| Color palette templates (50+) | V | ✅ 52 seeded |
| Lighting presets + custom (color/brightness/diffusion/angle) | V | ✅ 6 presets + custom |
| Speed ramps (8) | V | ✅ |
| Camera-moveset "cinematographer styles" | V | ✅ 10 seeded |
| Character emotion intensity slider | V | 🟡 (rendered into prompt text; provider-dependent realness) |
| Native synchronized audio | V | provider-dependent; surfaced honestly in capability registry |
| Duration up to 30s | V | ✅ duration selector with per-model caps |

## D. Characters & references

| Capability | Reference evidence | Status |
| --- | --- | --- |
| Train character from 20–80 photos | V | 🔧 training job implemented; identity training requires an engine that supports it (documented, keyless = explicit status) |
| Reference-strength reuse per generation | V | ✅ |
| Saved elements (character/location/prop) reusable across projects | V | ✅ elements table + pickers |
| Emotion/consistency POV honesty ("same person", not pixel-perfect) | V | ✅ copy reflects limits |

## E. Economy

| Capability | Reference evidence | Status |
| --- | --- | --- |
| Credits as generation currency, per-model cost preview on Generate button | V | ✅ |
| Credit types: subscription/pack/auto-refill/promo/boost | V | ✅ ledger models for all five |
| Spend order: subscription first, then soonest expiry | V | ✅ |
| Auto-refund on failed generation | V | ✅ transactional refund in job failure path |
| Usage history w/ per-model breakdown | V | ✅ |
| Subscriptions + checkout (Stripe) | V (payments exist) | 🔧 Stripe checkout + webhook code; needs STRIPE keys |
| Admin-controlled plan config | V | ✅ |
| Concurrency boost semantics | V | ✅ per-tier concurrency limiter |

## F. Rollout interfaces

| Capability | Reference evidence | Status |
| --- | --- | --- |
| Web MCP / CLI equivalents | V | ✅ API keys + REST generation endpoints (agent-ready) |
| Node-based multi-model board | V | ⬜ Flowboard backlog |
| Agent (brief→plan→assets) | V | ⬜ Mission Control backlog |

## G. Deliberately NOT reproduced

- Any reference-brand visual identity, logo, fonts, or copy.
- Scraped community galleries or teaser videos.
- Anything requiring bypassing the reference product's auth, paywalls, or protected-content systems.
