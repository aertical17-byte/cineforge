# SECURITY

## Implemented controls

| Area | Control |
| --- | --- |
| Passwords | bcrypt (cost 12) + policy (≥10 chars, digit, uppercase) |
| Sessions | JWT HS256, iss/iat/exp verified, 14d TTL, bearer-only (no CSRF cookie surface) |
| API keys | stored as SHA-256 digest + 12-char prefix for lookup; constant-time compare; revocation |
| Authorization | per-row user_id scoping enforced in every query path; admin role gate |
| Rate limiting | DB-backed rolling windows; auth 20/min/IP; API 120/min/identity (Redis-ready hook) |
| Input validation | Pydantic bodies; regex-free bounded fields; idempotency unique constraint |
| Upload safety | magic-byte sniff (png/jpeg/webp), ≤32MB, MIME whitelist, content-type nosniff header |
| File serving | absolute-path confinement + HMAC-TTL signed URLs (local mode); S3 presign in prod |
| SQL injection | SQLAlchemy bound parameters everywhere; no string interpolation |
| XSS | React escaping; no dangerouslySetInnerHTML; strict CSP is on the D1 backlog |
| Headers | X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy middleware |
| Secrets | env-only; .env.example templated; nothing committed; /v1/providers exposes booleans only |
| Provider KPI honesty | capability registry: UI shows only real capabilities; unsupported param ⇒ degraded or 422 (never faked) |
| Mock mode | requires ENVIRONMENT=test; production bootstrap refuses AI_MOCK_MODE (honest error) |
| Audit | auth events, admin action, billing events, mutating HTTP (post-auth user binding) in audit_logs |
| Abuse prevention | plan concurrency caps + per-minute limits; reports of abuse → admin revoke paths |
| Likeness policy | consent flag required before character identity creation (surface level; policy enforced at gate) |

## Deliberately not-yet (tracked on roadmap)

- CSP + HSTS at ingress (deployment concern), 2FA, session revocation list, storage-side virus scan, per-tenant encryption keys.

## Data-protection notes

- Card data: none stored anywhere (Stripe token flow only).
- Likeness data: photo vaults for character training are user-scoped assets; deletion cascades soft-delete; export available (asset download).
- Provider payloads: prompts/references are sent to the configured AI provider — documented in the UI notice plane (operator-configured privacy addendum required for enterprise deployments).
