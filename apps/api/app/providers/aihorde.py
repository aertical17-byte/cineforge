"""AI Horde adapter — genuinely free, keyless community generation (budget-0 deployments).

Per the AI Horde project (open source: github.com/Haidra-org/AI-Horde, service at aihorde.net):
volunteers share GPU time; anonymous access works with the well-known public key of ten
zeros ("0000000000") at reduced concurrency/size. No signup, no card, no quota purchase.

Integration honesty:
- anonymous tier: ~512px long side, ~1 concurrent job per key, queue waits are normal →
  429 responses raise ProviderError so the worker requeues with backoff instead of failing.
- images only: the horde does not serve video jobs via this free path; video requests raise
  ProviderUnsupported and the API surfaces that honestly.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import httpx

from app.providers.base import (AIProvider, GenerateResult, ImageRequest, JobState,
                                ProviderError, ProviderUnsupported, VideoRequest,
                                poll_until)

BASE = "https://aihorde.net/api/v2"

ANON_KEY = "0000000000"

# anonymous tier refuses >~580px on the long side; we stay at 512 to be safe.
ASPECT_WH = {
    "1:1": (512, 512), "16:9": (512, 288), "9:16": (288, 512),
    "4:3": (512, 384), "3:4": (384, 512),
}

POLL_INTERVAL_S = 5.0
POLL_MAX_S = 480.0


def horde_size(aspect_ratio: str) -> Tuple[int, int]:
    return ASPECT_WH.get(aspect_ratio, (512, 512))


def horde_payload(req: ImageRequest) -> Dict[str, Any]:
    """Pure payload builder (unit-tested without network)."""
    width, height = horde_size(req.aspect_ratio)
    prompt = req.prompt if not req.negative_prompt else f"{req.prompt} ### {req.negative_prompt}"
    params: Dict[str, Any] = {"width": width, "height": height, "n": 1,
                              "steps": min(int(req.steps or 25), 50)}
    if req.seed is not None:
        params["seed"] = int(req.seed) % 2**32
    if req.guidance:
        params["cfg_scale"] = float(req.guidance)
    return {"prompt": prompt, "params": params, "nsfw": False, "r2": True}


class AIHordeProvider(AIProvider):
    id = "aihorde"

    def __init__(self, api_key: str = ANON_KEY, client_agent: str = "CineForgeAI:0.2:cineforge"):
        self.api_key = api_key or ANON_KEY
        self.client_agent = client_agent or "CineForgeAI:0.2:cineforge"

    def _headers(self) -> Dict[str, str]:
        return {"apikey": self.api_key, "Client-Agent": self.client_agent,
                "Content-Type": "application/json"}

    async def generate_image(self, req: ImageRequest) -> GenerateResult:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{BASE}/generate/async", json=horde_payload(req),
                                  headers=self._headers())
            if r.status_code == 429:
                # anonymous tier allows ~1 concurrent job per key: backoff-and-retry, not fail
                raise ProviderError("aihorde: anonymous concurrency limit hit, will requeue")
            if r.status_code >= 400:
                raise ProviderError(f"aihorde submit refused {r.status_code}: {r.text[:200]}")
            job_id = r.json().get("id", "")
            if not job_id:
                raise ProviderError("aihorde submit returned no job id")

        async def step():
            async with httpx.AsyncClient(timeout=60) as client:
                c = await client.get(f"{BASE}/generate/check/{job_id}", headers=self._headers())
                if c.status_code == 404:
                    raise ProviderError("aihorde job vanished (expired or purged)")
                if c.status_code >= 400:
                    raise ProviderError(f"aihorde check {c.status_code}")
                chk = c.json()
            if chk.get("faulted"):
                raise ProviderError("aihorde job faulted in the volunteer queue")
            if chk.get("cancelled"):
                return JobState.canceled, None, {}
            if chk.get("done"):
                async with httpx.AsyncClient(timeout=60) as client:
                    st = await client.get(f"{BASE}/generate/status/{job_id}", headers=self._headers())
                    if st.status_code >= 400:
                        raise ProviderError(f"aihorde status {st.status_code}")
                    data = st.json()
                gens = data.get("generations") or []
                if not gens or not gens[0].get("img"):
                    raise ProviderError("aihorde finished with no image")
                g0 = gens[0]
                meta = {"seed": g0.get("seed"), "horde_model": g0.get("model"),
                        "censored": g0.get("censored"), "wait_time": chk.get("wait_time")}
                return JobState.succeeded, [g0["img"]], meta
            return JobState.running, None, {"queue_position": chk.get("queue_position"),
                                            "wait_time": chk.get("wait_time")}

        state, urls, meta = await poll_until(step, interval_s=POLL_INTERVAL_S, max_seconds=POLL_MAX_S)
        if state != JobState.succeeded or not urls:
            raise ProviderError(f"aihorde job ended as {state}")
        return GenerateResult(kind="image", urls=urls, provider_job_ref=job_id,
                              native_metadata=meta)

    async def generate_video(self, req: VideoRequest) -> GenerateResult:
        raise ProviderUnsupported("aihorde serves images only on the free community path")

    async def cancel(self, ref: str) -> JobState:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.delete(f"{BASE}/generate/status/{ref}", headers=self._headers())
        except Exception:  # noqa: BLE001 — cancel is best-effort
            return JobState.running
        return JobState.canceled
