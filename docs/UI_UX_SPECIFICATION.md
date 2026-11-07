# UI/UX SPECIFICATION — CineForge AI

Design system + interface behavior, derived from the research inventory (docs/PRODUCT_RESEARCH.md) and re-authored as an original, independent visual identity. **No visual asset of the reference product was copied.**

## 1. Design tokens

| Token | Value | Usage |
| --- | --- | --- |
| bg | `#08080c` (ink-950) | app background |
| surface | `#0d0d13` / `#13131b` | cards (ink-850/900) |
| border | `#23232f` | hairline structure (ink-700) |
| accent | `#7c5cff` (byz-500) | CTAs, active states, focus rings |
| accent soft | `#b3a2ff` (byz-300) | active text on dark |
| signal red | `#ff5c7a` (ember) | destructive/error |
| success | `#34d399` (emerald-300) | "ready" states |
| radius | 1rem / 1.125rem (xl2) | cards/buttons |
| shadow | layered card + purple glow | primary CTA only |
| type | Inter; display 600 tracking-tight; UI 400/500 | sans stack |
| spacing scale | 4pt grid (1–6 spans) | all gaps/padding |
| motion | 150–250ms ease; reduced-motion respected | hover/tabs/modal |

Reference-inspired *behavioral vocabulary* (dark cinematic canvas, gallery-first, one accent, caps micro-labels for sections) — implemented with an original palette, type rhythm and component anatomy.

## 2. Layout grammar

- **Landing**: sticky slim nav (wordmark · log in · CTA) → hero with gradient orb + underline CTA (Start free — 200 credits) → 6-card feature grid → preset strip (chips) → slim footer with non-affiliation line.
- **Studio (auth)**: fixed 240px left rail (sections Create/Work/Inspiration + Settings/Admin), sticky top bar (right-aligned credits badge, "New generation"), content column max-full with 20–32px gutters.
- Generative screens: **two-column workspace** — 380px control stack (prompt card, engine card, references card) vs. right stage (camera panel card, results card with skeleton→asset states).

## 3. Components (implemented in `apps/web/components`)

ui.tsx: `Button` (primary/ghost/outline/danger × sm/md/lg), `Input`, `Card`, `Badge` (neutral/accent/warn/err/ok), `Modal`, `Tabs` (aria roles), `Field` (label+hint), `EmptyState`, `Skeleton`.
shell.tsx: `Sidebar` (icon+label nav, active=byz tint, admin-gated entries), `TopBar` (live credits via 15s query refetch).
workspace.tsx: `Workspace` (tabs for text→X/image→X, prompt textarea 4000, negative prompt gated by capability, engine select, aspect chips, duration slider 1–max, batch slider, seed input when supported, project select, reference uploading grid with per-ref delete, **Generate · <n> credits** always shows cost), `SetupSelect` dropdowns (10 film-setup axes), camera move grid (22 buttons, tooltip=fragment), `ResultsPanel` (status badges, skeletons while running, asset tiles with download, failure copy **with auto-refund note**).

## 4. Interaction & states

- Cost-of-intent: the button label always shows the deterministic credit estimate before submission ("Generate · 14 credits") — cost preview is part of the UI contract, matching the reference's pre-confirm price display `[V]`.
- Progress: tile skeletons + status pill (`queued…` / `running…`) polling every 2.5s; terminal states flip badges.
- Failure: explicit error panel, red border style, error_code + message, **"credits refunded automatically"** note; retry = re-roll button (history & workspace).
- Empty states: every collection has a dashed empty card with an action CTA.
- Loading: skeletons for cards/tables; total layout stable while loading.
- Responsive: ≤xl collapses workspace to single column; sidebar stays fixed down to md; touch targets ≥40px.
- A11y: semantic headings, aria-selected tabs, labelled inputs (Field), focus-visible ring on accent color.
- Copy tone: honest capability labels ("model ignores refs", "camera → prompt text") — the UI never oversells what an engine can't do.

## 5. Screen inventory (all wired)

/, /login, /register, /forgot-password, (studio): dashboard, create/image, create/video, create/edit, projects, projects/[id], library, history, presets, templates, characters, tools, settings (→profile), settings/profile, settings/billing, settings/subscription, admin.

## 6. Future visual polish backlog

- Motion: framer-motion transitions on gallery/cards (dependency present).
- Preview lightbox (component present; wiring listed in D1).
- Drag-drop reference reorder.
