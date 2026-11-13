CineForge AI — first launch (v0.6.0)
====================================

LIGHT MODE — the default. Nothing to install, no Docker, no 6 GB of disk:

1) Drag "CineForge AI" into the Applications folder (arrow on the right).
2) Open the app: a window appears and the Light Studio opens in your browser
   automatically (localhost:3000 redirects to the hosted studio).
   The app itself is ~2 MB: it only launches your browser.
3) In the studio, "Image Atelier" generates AI images for free — the community
   engine (AI Horde) runs on volunteers' GPUs, no card, no signup, no API key.
   Queue is usually 30-120 s: that's the honest price of free.
4) The catalog shows every room honestly: green = works free now,
   violet = needs an engine that isn't free yet (bring your own key).

FULL LOCAL MODE — optional, for the complete product (projects, Flowboard,
local library, your own engine keys):

1) Open the app → "Full local mode (Docker) — show options".
2) Click "Set up the full local mode (Docker)". You need Docker Desktop
   (free): if it's missing, the app takes you to the download page.
   The first launch downloads and builds: 5-15 minutes.
3) When it's ready http://localhost:3000 opens with the complete app:
   no signup (automatic guest session), unlimited credits
   (1,000,000 welcome ones, never expiring).

If macOS says the app "cannot be opened" (normal: no paid Apple signature):
- System Settings → Privacy & Security → "Open Anyway" → Open, or
- in Terminal:  xattr -dr com.apple.quarantine "/Applications/CineForge AI.app"

To stop the full local mode: open the app → "Stop services".
The Light Studio needs no stopping — close the browser tab and you're done.
Full guide and troubleshooting: guida.html inside the app ("Guide" button).
