# PRODUCT RESEARCH — Independent Alternative to the Higgsfield AI Creative Suite

> Scope, ethics, and honesty rules for this document:
> - Everything below comes from **publicly accessible** pages of higgsfield.ai (its marketing site and its "Creator Hub" help center) that were loaded on **2026-11-05..07 UTC**, plus one live homepage session inspected with an automated browser (viewport-level structure only).
> - Descriptions are **paraphrased in our own words**. No text, image, logo, or other asset from the reference site has been copied into this project.
> - The product we build (**CineForge AI**) is an **independent implementation** of comparable *functionality*. Feature names of generic cinematography concepts (dolly, crane, orbit, pan…) are industry vocabulary, not proprietary property. Branded names of the reference product ("Soul", "DOP", "Cinema Studio", etc.) are referenced here **only as research identifiers** and are never used in our product or code.
> - Nothing in this document claims access to undocumented internal architecture. Every claim is tagged: `[V]` = verified by reading a public page / live DOM, `[H]` = hypothesis or extrapolation, `[P]` = proposed extension of our own.

---

## 1. Method

| Instrument | What it produced |
| --- | --- |
| Automated browser session on the live homepage | Navigation structure, hero modules, section rhythm, CTAs |
| Public help-center articles (Creator Hub) | Model families, tool semantics, credit rules, character training rules |
| Web search across third-party 2026 reviews | Cross-check that our reading matches observed usage; flagged as secondary evidence |

Research limitations: we did **not** create an account on the reference product; the logged-in workspace itself screens (asset library internals, exact checkout, admin pages) are therefore `[H]` unless reproduced in the product. No screenshots of the reference interface are stored in this repo (licensing conservatism + they age badly). Instead we record *described layouts* and rebuild **equivalent, original** interfaces.

## 2. Verified product picture `[V]`

### 2.1 Landing page (live DOM, 2026-11-07)

- Global top bar: wordmark left; search; "Enterprise", a pricing link with a discount badge, Login, and a primary "Get started" button on the right.
- Content model of the hero area: a **rotating/stacked announcement list** of flagship launches (video model, agent, influencer tool), a discount-capture module, then **large editorial sections per flagship capability** ("Shorts" preset studio, community project explorer), each with a gallery of items and a "View all" link.
- Community section: showcases **projects with prompt/asset transparency** ("see how each project was created") — the site treats *shared prompts + assets* as marketing material.
- Tone: dark, cinematic, typographic, all-caps section headers.

Implication for our product: launch-driven, gallery-heavy landing; every section links into a transactional workspace. `[V]`

### 2.2 Model families (help center, paraphrased) `[V]`

Image: a native "signature look" family (fashion/cinematic, with a trained-identity feature for consistency), a storyboarding family, plus third-party engines split by strength (fast + reference control / text rendering / visual reasoning / speed / vector-style).
Video: a global cinematography layer **applied as presets on top of other models**; plus third-party engines per strength (realistic human motion / long multi-shot / first-and-last-frame control / synchronized audio / Google's model / fast-dynamic).
Audio: text-to-speech, expressiveness, multilingual, all-in-one scene audio — exposed through voiceover/translation/lipsync surfaces. `[V]`

Semantics we reproduce independently:
- **Model families, not version-picking**: user picks a family; platform resolves "latest". `[V]`
- **Credit cost varies by model/resolution/duration, shown on the Generate button before confirm.** `[V]`
- **Model availability gated by plan tier.** `[V]`

### 2.3 Tools (help center, paraphrased) `[V]`

| Reference tool | Our independent equivalent (working names) | Essence |
| --- | --- | --- |
| "Cinema Studio" | **Director's Room** | Filmmaking workspace: per-shot camera/lens/focal/aperture, global genre/era/palette/lighting/move-set style, multi-reference input, native audio, extend forward/backward, regional video edit |
| "Marketing Studio" | **Ad Lab** | Product ads/UGC from a product image or URL |
| "AI Influencer" | **Persona Builder** | Menu-driven consistent character creation (attributes via UI, not prompts) |
| "Canvas" | **Flowboard** | Node-based chaining of models; shares work as templates; team boards |
| "Supercomputer" | **Mission Control** (agent) | Brief → plan → assets; scheduled tasks; external connectors |
| MCP / CLI | API + personal API keys | Programmatic access with the same credits |

Additional verified micro-features to reproduce as equivalents: `[V]`
- Genre set: General/Action/Horror/Comedy/Noir/Drama/Epic. Speed ramps: Linear/Auto/Flash-in/Flash-out/Slow-mo/Bullet time/Impact/Ramp-up.
- Camera/lens/aperture per shot; era + tempo ("cut speed" from single shot to chaotic); **50+ color-grading templates**; lighting presets + custom (color/brightness/diffusion/angle); camera moves incl. POV, robot arm, helicopter shot.
- Character **emotion intensity slider**; clips up to 30s; up to 50 references on the newest tier (9 on older); protected-content/real-face refusal states surfaced to users.
- "Elements": saved reusable characters/locations/props, project-scoped but pullable across projects; reference picker can attach uploads, past generations, and liked assets.

### 2.4 Character consistency (help center, paraphrased) `[V]`

- Train a reusable identity from **20–80 photos of one person**; training takes minutes; identity then selectable at generation time and reusable across the family + carried into some other engines via the saved-elements mechanism.
- Photo-set quality rules (angles/expressions variety, good light, recent shots, ≥1 full-height, single subject).
- Honest expectation-setting: "clearly the same person", not pixel-identical; drift under extreme style shifts.
- Emphasis on likeness consent (upload only your own or permitted likeness).

### 2.5 Credit economy (help center, paraphrased) `[V]`

- Five credit types: subscription (resets each cycle, no rollover), one-time packs (expire 90 days), auto-refill (expires 90 days), promo (expiry on issue), boost/concurrency.
- **Spend order: subscription first, then soonest expiry.** `[V]`
- Free generations / unlimited lists are web-only, model-specific, non-renewing.
- **Failures are auto-refunded within minutes** (with model-specific exceptions); full usage log with per-model breakdown lives under account → usage. `[V]`
- Balance in top bar; detailed breakdown under account → subscription.

### 2.6 Pricing/public plans `[V-partial]`
Public pricing page advertises tiered subscriptions with model gating and discount windows. Exact SKUs change frequently; we therefore implement **admin-controlled plan configuration** in our DB instead of hard-coding competitor SKUs. `[P]` for exact prices.

## 3. Route map observed `[V]` (public, unauthenticated)

- `/` landing; sections per flagship; community explorer; footer marketing routes
- `/ai-video`, `/pricing`, `/enterprise`, `/contact`, `/blog/*`
- `/creator-hub/help-center/**` (AI models, tools, credits, billing, troubleshooting, integrations)
- Auth surface: `Login` and `Get started` open authentication flows (exact internal screens not observed → our register/login/forgot pages implement the equivalent UX)

## 4. User journeys (described, original wording)

1. **Discovery → signup**: land on a launch section → click pricing/get started → auth → onboarding into a workspace with a credits balance visible top-right.
2. **First image**: pick the signature family, choose a style preset, write prompt, see credit cost on the button, generate, watch progress, land in a gallery; asset immediately reusable as reference.
3. **Character**: upload a portrait set → train → name → select as character in later generations; save as a reusable element.
4. **Short video**: enter the directing workspace → pick model family → choose camera move preset → tune lighting/genre → generate with native audio → extend or edit regionally → download.
5. **Rerun/iterate**: open a historical generation, duplicate its exact settings, re-roll, or send output as input to the next stage (image → video).

## 5. Unverified assumptions & hypotheses `[H]`

1. The logged-in workspace is a persistent left-rail + canvas layout (standard for this product class) — our implementation follows that pattern as an original design.
2. Generation concurrency limits exist per tier (evidenced by "boost/concurrency" credit type) — we implement a seat-level concurrency limiter.
3. Preset effects are model-agnostic *prompt engineering + provider parameters*, since the same presets appear across many engines — hence our preset system composes prompt modifiers and only emits provider params a model actually supports.
4. Reference-site "latest version" resolution is server-side per family.

## 6. Legal & product boundaries adopted by this project

- Independent name, typography, palette, copy, iconography: no mirroring of the reference brand.
- No scraping of reference galleries; sample content is generated/first-party only.
- Only features reachable via the public site are claimed as "reference parity"; everything else is labelled a **CineForge extension**.
- Camera/audio effects translate to real provider capabilities; when a provider can't do an effect, the UI says so instead of faking it.
