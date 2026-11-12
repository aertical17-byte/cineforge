# 🎬 CineForge AI

**Uno studio di AI per creare immagini e video — nel tuo browser, senza spendere un euro.**

[![CI](https://github.com/aertical17-byte/cineforge/actions/workflows/ci.yml/badge.svg)](https://github.com/aertical17-byte/cineforge/actions/workflows/ci.yml)

> Include un **motore gratuito** (AI Horde): genera immagini AI con **0 €, senza carta di credito e senza registrazione**. I motori "pro" (video, 4K) sono opzionali e restano disattivati finché non ci metti *tu* una chiave API.

---

## 🤔 Cos'è, in tre righe?

CineForge AI è una web app che ti fa:

- 🖼️ **generare immagini** con l'AI (gratis, con il motore community incluso)
- 🎬 **organizzare progetti** come sul set di un film: preset di camera, look, emozioni
- 🧩 **collegare i passi** in sequenze (Flowboard) e ritrovare tutto nella libreria

---

## 🚀 Prova sul tuo Mac (il modo facile)

1. **Scarica l'installer** → [ultime release → file `CineForge-AI.dmg`](https://github.com/aertical17-byte/cineforge/releases/latest)
2. Apri il file scaricato e **trascina «CineForge AI» in Applicazioni**
3. Avvia l'app e clicca **«Prepara e avvia CineForge sul mio Mac»** — l'app scarica il codice, avvia i servizi e apre il browser quando è pronto (il primo avvio scarica molto: **5–15 minuti**)

> ✅ Requisiti: macOS 13+ e [Docker Desktop](https://www.docker.com/products/docker-desktop/) (gratuito). L'app controlla da sola e ti guida se manca qualcosa.
> 📖 Guida illustrata passo-passo: **[cineforge-iota.vercel.app/guida.html](https://cineforge-iota.vercel.app/guida.html)**

<details>
<summary>⚠️ Il Mac dice che l'app «non può essere aperta»? (normale, 1 minuto)</summary>

L'installer è gratuito e senza firma Apple a pagamento, quindi macOS fa una domanda in più:

- **Clic destro** su «CineForge AI» → **Apri** → **Apri**
- Su macOS recenti: **Impostazioni di sistema → Privacy e sicurezza → «Apri comunque»**
- Ultima spiaggia (terminale): `xattr -dr com.apple.quarantine "/Applications/CineForge AI.app"`
</details>

---

## 💻 Chi non ha un Mac (o preferisce i comandi)

Con [Docker](https://www.docker.com/get-started/) installato:

```bash
git clone https://github.com/aertical17-byte/cineforge.git
cd cineforge
docker compose --project-directory . -f infra/docker/docker-compose.yml up -d --build
# quando è pronto: http://localhost:3000
```

---

## 🎥 La tua prima immagine (gratis, davvero)

1. Su `http://localhost:3000` **registrati** → arrivi con **200 crediti gratis**
2. Apri uno studio → scegli il motore **«AI Horde · community (free, no key)»**
3. Scrivi il prompt e genera ⚡

Cosa aspettarsi (onestamente):

| | |
|---|---|
| 💸 Costo | **0 €** — volontari condividono le loro GPU (progetto open: [AI Horde](https://github.com/Haidra-org/AI-Horde)) |
| 🐢 Velocità | A volte devi aspettare in coda (30–120 s) — per questo costa zero |
| 🖼️ Qualità | ~512 px, buone per storyboard e bozze |
| 🎥 Video | Il motore gratuito fa solo immagini; i video richiedono un motore a pagamento opzionale (chiave tua, mai inclusa qui) |

**Mai successi finti**: se un motore non è configurato, l'app te lo dice chiaramente (`provider_not_configured`) e ti restituisce i crediti — niente immagini fasulle.

---

## 📂 Com'è fatto dentro (per i curiosi)

| Pezzo | Cosa fa | Dove |
|---|---|---|
| 🌐 Web app | Tutto ciò che vedi nel browser | `apps/web` (Next.js) |
| ⚙️ API | Il "cervello": account, crediti, code | `apps/api` (FastAPI) |
| 🔁 Worker | Genera davvero le immagini | `apps/api` (loop dedicato) |
| 🐳 Docker | Avvia tutto con un comando | `infra/docker/` |

Tutto il resto della documentazione: **[`docs/`](docs/)** — architettura, sicurezza, specifica API, test.

---

## 🛠️ Per sviluppatori

- **CI**: 4 job a ogni push (test API su Postgres+Redis, typecheck+build web, E2E browser, build container) — vedi `.github/workflows/ci.yml`
- **Prova live senza chiavi**: tab *Actions* → `live-smoke` genera 1 immagine reale via AI Horde con **zero credenziali** e la carica come artefatto
- **Stato del progetto**: [`PROJECT_STATUS.md`](PROJECT_STATUS.md) · roadmap: [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md)
- Test rapidi: `cd apps/api && python -m pytest -q` · `cd apps/web && npm run test`

### Licenza / nota di indipendenza

Progetto originale e indipendente: ispirato solo a funzionalità *osservabili pubblicamente* di altri prodotti AI; nessun asset, testo di marketing o codice di terzi. Vedi `docs/PRODUCT_RESEARCH.md`.

---

<details>
<summary>🇬🇧 English TL;DR</summary>

CineForge AI is an independent AI creative platform (image generation, cinematography presets, projects, credits, media library). It ships with a **genuinely free, keyless image engine** (AI Horde community) — no credit card, no signup. Mac users: download the `.dmg` from Releases, drag to Applications, click *Start* (needs free Docker Desktop). Everything else: `docker compose up` on any machine. Pro engines (video/4K) stay honestly disabled until you add your own API keys. Full docs in `docs/`.
</details>
