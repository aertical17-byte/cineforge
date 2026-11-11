# DEPLOYMENT CHECKLIST

## A. Prerequisites (operator)

- [ ] A server/host with Docker (Railway/Fly.io/Render/VPS or GitHub-runner box)
- [ ] Postgres 16 (managed or the compose service)
- [ ] Generating `JWT_SECRET` (≥64 random chars)
- [ ] Optional: REPLICATE_API_TOKEN and/or FAL_KEY (provider engines)
- [ ] Optional: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_MONTHLY/YEARLY (real Stripe Price IDs)
- [ ] Optional S3-compatible bucket + keys (else local-disk storage works for a single host)

## B. Bring-up (compose)

1. `cp .env.example .env` → fill values.
2. Either run `bash infra/deploy.sh` (builds, starts, waits for `/health`), or manually:
   `docker compose -f infra/docker/docker-compose.yml up -d --build`
3. Health: `curl api:8000/health` → `{"ok":true}`
4. First operator: set `ADMIN_EMAILS=you@yourdomain` then register with that email (admin is granted at registration time).
5. Verify `/v1/providers` reflects your configured engines.

## C. Live verification requested per master plan

- [ ] `make verify-providers` (or the CI step with repo secrets REPLICATE_API_TOKEN/FAL_KEY)
- [ ] Register a test account → welcome credits visible in top badge
- [ ] Generate an image (engine tier available to free plan) → asset in library; ledger shows −cost
- [ ] Stop a provider (unset key) → generation fails cleanly with `provider_not_configured` + **automatic refund visible in Billing ledger**

## D. Security hardening before public traffic

- [ ] TLS at ingress (Caddy/NLB/Cloudflare) + HSTS
- [ ] Rotate JWT_SECRET; POSTGRES password; disable compose-exposed DB port
- [ ] Log shipping + uptime monitor on `/health` and worker liveness
- [ ] Backups: `"pg_dump"` nightly + storage bucket versioning

## E. Known deployment limits (honest)

- Single-volume local storage mode is not horizontally scalable → use S3 mode for multi-node.
- SMTP is not wired → password recovery stays manual until an SMTP account is added.
- Stripe checkout requires real Price IDs created in your Stripe dashboard (env vars documented).
