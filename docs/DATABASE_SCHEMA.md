# DATABASE SCHEMA — CineForge AI

PostgreSQL (prod) / SQLite (CI). Source of truth: `apps/api/app/models.py`; migration `0001_initial` applies metadata (no drift possible); later migrations via alembic autogenerate. `docs/DATABASE_SCHEMA.md` prose ↔ models mapping below.

## Entity–relation map

```
users 1─0..1 profiles          users 1─* api_keys        users 1─* notifications
users 1─* projects 1─* assets  users 1─* generations 1─* generation_jobs
assets (source=upload|generation)             uploads
users 1─* credit_transactions                 plans ─* subscriptions
elements (character|location|prop) ─* element_photos ─1 assets
ai_providers ─* ai_models                     preset_rows (generic registry)
templates                                     payments ─1 invoices
usage_logs / audit_logs / rate_limit_rows
```

## Tables (key columns; all PKs are UUID-strings except audit_logs/credit id variants noted)

- **users**(id PK, email uq idx, password_hash, display_name, avatar_asset_id FK→assets, is_active, is_admin, consent_likeness, created_at, updated_at, deleted_at) — soft delete.
- **profiles**(id PK, user_id uq FK, bio, company, timezone, prefs JSON).
- **credit_transactions**(id PK, user_id idx, kind[: subscription|pack|auto_refill|promo|boost|refund], amount signed int, remaining int (lot semantics), source[: signup|purchase|spend|refund|admin|renewal], generation_id FK nullable, expires_at idx nullable, created_at idx; composite idx user/kind/expiry for the spend-order query).
- **plans**(code uq: free|creator|studio|enterprise; monthly_price_cents, yearly_price_cents, monthly_credits, max_concurrency, unlimited_models JSON, features JSON) — admin-controlled pricing.
- **subscriptions**(user_id idx, plan_code FK, status[: active|past_due|canceled], interval, current_period_end, stripe ids).
- **projects**(user_id idx, name, description, is_archived, timestamps, deleted_at) — soft delete.
- **generations**(user_id, project_id, media_type[: image|video], task[: text2img|img2img|text2video|img2video|video_ref|edit_video|extend_video|upscale], model_id FK, prompt, negative_prompt, params JSON, estimated_credits, actual_credits, status idx, error_code, error_message, batch_size, **idempotency_key + (user_id, idempotency_key) unique**, created_at idx, completed_at; idx user/created, project/created).
- **generation_jobs**(generation_id idx, attempt, status, claimed_by, claimed_at (lease), scheduled_at (backoff), provider_job_ref idx, log JSON).
- **assets**(user_id idx, project_id FK, generation_id FK, source[: upload|generation], kind[: image|video|audio], storage_key uq, url, mime, size_bytes, width/height/duration_ms, thumb_storage_key, is_liked, created_at idx, deleted_at) — soft delete.
- **uploads**(user_id, asset_id, purpose[: reference|first_frame|last_frame|avatar], original_name, mime, size_bytes).
- **ai_providers**(id PK: replicate|fal|mock; docs_url, base_url, requires_key/settings-field, is_enabled).
- **ai_models**(id PK, provider_id FK, family idx, display_name, tasks JSON, capabilities JSON, credit_cost_base, credit_cost_per_second, min_plan, provider_model, provider_config JSON).
- **provider_registry_status**(provider_id PK FK, verified_at, notes) — operator verification marker.
- **preset_rows**(id, group idx [camera_moves|palettes|…], name, payload JSON) — seeded from shared registry JSON.
- **templates**(slug uq, name, category, media_type, preview_asset_id, prompt, settings JSON, is_public).
- **elements**(user_id idx, type[: character|location|prop], name, description, anchor_asset_id, training_status, training_provider_job, attributes JSON, timestamps, deleted_at) + **element_photos**(element_id idx FK, asset_id FK, checked).
- **notifications**(user_id idx, kind, level, title, body, link, read_at).
- **usage_logs**(user_id idx, event, model_id, credits_delta, meta JSON, created_at idx).
- **audit_logs**(autoincrement PK, actor_user_id, action, entity, entity_id, ip, detail JSON, created_at idx).
- **api_keys**(user_id idx, name, prefix, key_digest uq (SHA-256), last_used_at, revoked_at).
- **payments**(user_id idx, provider, kind[: subscription|credit_pack], amount_cents int, currency, status, stripe_session_id idx) + **invoices**(payment_id FK, number uq, issued_at, pdf_url).
- **rate_limit_rows**(scope idx, window_start float, count) — Redis-free limiter storage.

## Retention & deletion policy (implemented)

- Soft delete (`deleted_at`) on users/projects/assets/elements/generations; hard DB delete reserved for purge jobs (roadmap D3).
- `credit_transactions`/`usage_logs`/`audit_logs` retained indefinitely (accounting trail; the product's usage-history promise requires it).
- Signed local file URLs expire (3600s default) — matching presigned S3 semantics.

## Indexes of note

- `ix_credits_user_spend(user_id, kind, expires_at)` — the credit spend-order scan.
- `uq_gen_idem(user_id, idempotency_key)` — safe client retries.
- `ix_gen_user_created` — history pagination.
- lease tables scanned by `status` (+ `claimed_at`).
