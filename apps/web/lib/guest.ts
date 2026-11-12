/**
 * No-login mode: the product's included engines (AI Horde community, free) need no
 * credentials, so the studio mints an ephemeral guest account on first visit instead of
 * forcing a signup. The token is persisted in localStorage by the auth store; a new
 * browser profile simply gets a fresh guest. Honest caveat (shown nowhere as "account"):
 * a cleared localStorage means a new guest identity.
 */
import {jsonApi} from "./api";
import {useAuthStore} from "./store";
import type {User} from "./types";

type GuestResponse = {access_token: string; user: User};

let inflight: Promise<void> | null = null;

/** Idempotent: safe to call from several components; only one POST /v1/auth/guest happens. */
export function ensureGuestSession(): Promise<void> {
  const {token} = useAuthStore.getState();
  if (token) return Promise.resolve();
  if (!inflight) {
    inflight = (async () => {
      try {
        const res = await jsonApi<GuestResponse>("/v1/auth/guest", "POST");
        useAuthStore.getState().setAuth(res.access_token, res.user);
      } finally {
        inflight = null;
      }
    })();
  }
  return inflight;
}
