# 🎬 CineForge AI

**An AI studio for creating images and video — in your browser, without spending a cent.**

[![CI](https://github.com/aertical17-byte/cineforge/actions/workflows/ci.yml/badge.svg)](https://github.com/aertical17-byte/cineforge/actions/workflows/ci.yml)

> Ships with a **free engine** (AI Horde): generate AI images for **$0, no credit card, no signup**. "Pro" engines (video, 4K) are optional and stay disabled until *you* add an API key.

---

## 🤔 What is it, in three lines?

CineForge AI is a web app that lets you:

- 🖼️ **generate images** with AI (free, with the bundled community engine)
- 🎬 **organize projects** like a film set: camera presets, looks, emotions
- 🧩 **chain the steps** into sequences (Flowboard) and find everything in the library

---

## ⚡ Light mode — nothing to install (v0.6.0+, no Docker, no 6 GB)

Since v0.6.0 the Mac app opens **the Light Studio in your browser by itself** (the app runs a tiny redirect on `localhost:3000` to the hosted studio):

- 🖼️ **Free image generation, right now**: the community engine (AI Horde) runs client-side in your browser — no Docker, no disk space, no card, no signup, no API key
- 🎥 **22 camera moves + director presets** (genres, palettes, lighting, lenses, eras — the real registries) composed into your prompt
- 🗂 **Every room honestly labeled**: what works free today vs. what needs your own engine key — nothing pretends
- 🪶 The launcher is ~2 MB. Nothing else touches your Mac; the studio page itself is hosted for free and builds on GitHub Actions

The **full local mode** (optional, Docker Desktop required) still gives you the complete product: projects, Flowboard, local library, your own engine keys.

---

## 🚀 Try it on your Mac (the easy way)

1. **Download the installer** → [latest release → the `CineForge-AI.dmg` file](https://github.com/aertical17-byte/cineforge/releases/latest)
2. Open the downloaded file and **drag "CineForge AI" into Applications**
3. Launch the app: the **Light Studio opens in your browser automatically** — you're already creating (free engine, no Docker). For the complete product, click **"Full local mode (Docker) — show options"** → the app downloads the code, starts the services and opens your browser when it's ready (the first run downloads a lot: **5–15 minutes**)

> ✅ Requirements: macOS 13+ and [Docker Desktop](https://www.docker.com/products/docker-desktop/) (free). The app checks by itself and guides you if something is missing.
> 📖 Illustrated step-by-step guide: **[cineforge-iota.vercel.app/guida.html](https://cineforge-iota.vercel.app/guida.html)**

<details>
<summary>⚠️ macOS says the app "cannot be opened"? (normal, 1 minute)</summary>

The installer is free and carries no paid Apple signature, so macOS asks one extra question. Any of these (once) works:

- **System Settings → Privacy & Security** → scroll down → **"Open Anyway"** → Open (works on every macOS, including Sequoia and newer)
- **Terminal** one-liner: `xattr -dr com.apple.quarantine "/Applications/CineForge AI.app"`
- On macOS 14 or older, **right-click** "CineForge AI" → **Open** → **Open** also works
</details>

---

## 💻 No Mac, or prefer commands

With [Docker](https://www.docker.com/get-started/) installed:

```bash
git clone https://github.com/aertical17-byte/cineforge.git
cd cineforge
docker compose --project-directory . -f infra/docker/docker-compose.yml up -d --build
# when it's ready: http://localhost:8766/studio/
```

---

## 🎥 Your first image (free, for real)

1. Open `http://localhost:8766/studio/` — **you're already in**: automatic guest session, no signup, **unlimited credits** (1,000,000 welcome ones, never expiring)
2. Open a studio → pick the engine **"AI Horde · community (free, no key)"**
3. Write the prompt and generate ⚡

What to expect (honestly):

| | |
|---|---|
| 💸 Cost | **$0** — volunteers share their GPUs (open project: [AI Horde](https://github.com/Haidra-org/AI-Horde)) |
| 🐢 Speed | Sometimes you wait in a queue (30–120 s) — that's why it costs nothing |
| 🖼️ Quality | ~512 px, good for storyboards and drafts |
| 🎥 Video | The free engine does images only; video needs an optional paid engine (your own key, never included here) |

**Never fake success**: if an engine isn't configured, the app tells you clearly (`provider_not_configured`) and refunds the credits — no fake images.

---

## 📂 How it's built (for the curious)

| Piece | What it does | Where |
|---|---|---|
| 🌐 Web app | Everything you see in the browser | `apps/web` (Next.js) |
| ⚙️ API | The "brain": accounts, credits, queues | `apps/api` (FastAPI) |
| 🔁 Worker | Actually generates the images | `apps/api` (dedicated loop) |
| 🐳 Docker | Starts everything with one command | `infra/docker/` |

The rest of the documentation: **[`docs/`](docs/)** — architecture, security, API spec, tests.

---

## 🛠️ For developers

- **CI**: 4 jobs on every push (API tests on Postgres+Redis, web typecheck+build, browser E2E, container build) — see `.github/workflows/ci.yml`
- **Live proof without keys**: *Actions* tab → `live-smoke` generates 1 real image via AI Horde with **zero credentials** and uploads it as an artifact
- **Project status**: [`PROJECT_STATUS.md`](PROJECT_STATUS.md) · roadmap: [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md)
- Quick tests: `cd apps/api && python -m pytest -q` · `cd apps/web && npm run test`

### License / independence note

Original and independent project: inspired only by *publicly observable* features of other AI products; no third-party assets, marketing text or code. See `docs/PRODUCT_RESEARCH.md`.
