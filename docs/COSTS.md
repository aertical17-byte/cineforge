# COST MODEL (verified from published provider pricing pages at authoring time)

Prices change — publish and re-check before go-live; credits are denominated so operator margins are configurable.

## Provider usage costs (per output)

| Engine (catalog id) | Provider | Published price basis (as flagged in catalog) | Our credit price |
| --- | --- | --- | --- |
| flux-schnell | Replicate | per-output image producer time ≈ $0.003 | 3 cr |
| flux-dev | Replicate | ≈ $0.025 | 12 cr |
| stable-diffusion-xl | Replicate | ≈ $0.01 | 4 cr |
| flux image-to-image (fal) | fal.ai | ≈ $0.02 | 4 cr |
| wan-2.2 t2v (keyframe-capable) | Replicate | per-second video, order $0.20–0.50/s | 10 + 4/s cr |
| kling standard t2v / i2v (fal) | fal.ai | per-second, order $0.14–0.40/s | 14 + 8/s cr |

Credit design: 1 credit ≈ $0.01 list (creator/tax unconsidered here); every tier configured in DB (admin-adjustable margin).

## Infra (single-region baseline, non-selling estimates)

| Component | Assumption | ≈ $/month |
| --- | --- | --- |
| Small web+api host (2 vCPU/4GB) | compose single host | 20–40 |
| Managed Postgres small | 10GB | 15–25 |
| Storage 100GB + egress small | S3-class | 5–10 |
| Redis (managed micro) | optional | 15 |
| Observability (basic) | hosted logs | 10 |
| **Σ fixed** | | **≈ 75–105** (before variable AI spend) |

Variable AI spend scales strictly with paid-by-user credits: passes pricing responsibility to admin-configured credit prices (see CSV in `docs/AI_ENGINE.md` §6). At the default margin table, break-even on the $99 studio tier occurs inside ~14-30 studio-tier months of infill.

## CI usage free tier

GitHub-hosted runners for OSS-private repos: minutes metered; the pipeline uses one GPU-less path all runtime under ~10 min/push (mock-only AI, no ML downloads).
