"""Replicate adapter (per Replicate's public HTTP API docs).

- Model resolution: `GET /v1/models/{owner}/{name}` returns `latest_version` — we resolve at call time
  so catalog rows never store version hashes that go stale.
- Predictions: `POST /v1/predictions` then poll ` PredictionResult` via `GET /v1/predictions/{id}`.
- Cancel per docs: `POST /v1/predictions/{id}/cancel`.

Field mapping uses common documented input names (prompt/negative_prompt/seed/...) and any
model-specific keys supplied in `provider_config.input_map`. Unverified endpoints are surfaced in
docs/AI_ENGINE.md and by `scripts/verify_providers.py`.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple

import httpx

from app.providers.base import (AIProvider, GenerateResult, ImageRequest, JobState,
                                ProviderError, ProviderNotConfigured, VideoRequest,
                                poll_until)

ASPECT_WH2H = {
    "1:1": (1024, 1024), "16:9": (1344, 768), "9:16": (768, 1344),
    "4:3": (1152, 864), "3:4": (864, 1152), "21:9": (1536, 640),
}


class ReplicateProvider(AIProvider):
    id = "replicate"
    base = "https://api.replicate.com/v1"

    def __init__(self, token: Optional[str]):
        self.token = token
        if not token:
            raise ProviderNotConfigured(self.id)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def _resolve_version(self, client: httpx.AsyncClient, model_ref: str) -> Tuple[str, Dict[str, Any]]:
        r = await client.get(f"{self.base}/models/{model_ref}", headers=self._headers())
        r.raise_for_status()
        data = r.json()
        version = data.get("latest_version") or {}
        return version.get("id", ""), version

    def _image_input(self, req: ImageRequest) -> Dict[str, Any]:
        return _common_input(
            req.provider_config, "prediction",
            prompt=req.prompt, negative_prompt=req.negative_prompt,
            width=ASPECT_WH2H.get(req.aspect_ratio, (1024, 1024))[0],
            height=ASPECT_WH2H.get(req.aspect_ratio, (1024, 1024))[1],
            seed=req.seed, reference_urls=req.reference_urls,
        )

    def _video_input(self, req: VideoRequest) -> Dict[str, Any]:
        return _common_input(
            req.provider_config, "prediction",
            prompt=req.prompt, negative_prompt=req.negative_prompt,
            duration=sounds_duration(req.duration_s), seed=req.seed,
            first_frame=req.first_frame_url, reference_urls=req.reference_urls,
        )

    async def _predict(self, model_ref: str, version_id: str, input_payload: Dict[str, Any]):
        async with httpx.AsyncClient(timeout=60) as client:
            if version_id:
                body = {"version": version_id, "input": input_payload}
                url = f"{self.base}/predictions"
            else:
                body = {"input": input_payload}
                url = f"{self.base}/models/{model_ref}/predictions"
            r = await client.post(url, json=body, headers=self._headers())
            if r.status_code >= 500:
                raise ProviderError(f"replicate server error {r.status_code}")
            r.raise_for_status()
            return r.json()

    async def _poll(self, pred_id: str):
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{self.base}/predictions/{pred_id}", headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def generate_image(self, req: ImageRequest) -> GenerateResult:
        model_ref = req.provider_model
        async with httpx.AsyncClient(timeout=60) as client:
            version_id, _ = await self._resolve_version(client, model_ref)
        pred = await self._predict(model_ref, version_id, self._image_input(req))
        return await self._await_output(pred)

    async def generate_video(self, req: VideoRequest) -> GenerateResult:
        model_ref = req.provider_model
        async with httpx.AsyncClient(timeout=60) as client:
            version_id, _ = await self._resolve_version(client, model_ref)
        pred = await self._predict(model_ref, version_id, self._video_input(req))
        return await self._await_output(pred)

    async def _await_output(self, pred: Dict[str, Any]) -> GenerateResult:
        pred_id = pred.get("id", "")

        async def step():
            p = pred if not pred_id else await self._poll(pred_id)
            status = p.get("status")
            if status == "succeeded":
                return JobState.succeeded, _extract(p.get("output")), p.get("metrics") or {}
            if status == "failed":
                raise ProviderError(f"replicate failed: {p.get('error')}")
            if status == "canceled":
                return JobState.canceled, None, {}
            return JobState.running, None, {}

        state, out, meta = await poll_until(step, interval_s=2.5)
        return GenerateResult(kind="media", urls=out or [], provider_job_ref=pred_id or "resolved-sync",
                              native_metadata={"metrics": meta})

    async def cancel(self, ref: str) -> JobState:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.base}/predictions/{ref}/cancel", headers=self._headers())
            return JobState.canceled if r.status_code < 400 else JobState.running


def _common_input(cfg: Dict[str, Any], mode: str, **kw) -> Dict[str, Any]:
    input_map: Dict[str, str] = (cfg or {}).get("input_map", {}) or {}
    fixed: Dict[str, Any] = (cfg or {}).get("fixed_input", {}) or {}
    payload: Dict[str, Any] = dict(fixed)
    if kw.get("prompt") is not None:
        payload[input_map.get("prompt", "prompt")] = kw["prompt"]
    if kw.get("negative_prompt"):
        payload[input_map.get("negative_prompt", "negative_prompt")] = kw["negative_prompt"]
    if kw.get("seed") is not None:
        payload[input_map.get("seed", "seed")] = int(kw["seed"])
    for src_key, dst_default in (("width", "width"), ("height", "height")):
        if kw.get(src_key) is not None:
            payload[input_map.get(src_key, dst_default)] = kw[src_key]
    if kw.get("duration") is not None:
        payload[input_map.get("duration", "duration")] = kw["duration"]
    refs = kw.get("reference_urls") or []
    if refs:
        key = input_map.get("first_reference", "image") if len(refs) == 1 else input_map.get("references", "image")
        if isinstance(key, str):
            payload[key if key else "image"] = refs[0]
    if kw.get("first_frame"):
        payload[input_map.get("first_frame", "input_image")] = kw["first_frame"]
    return payload


def sounds_duration(duration_s: int) -> int:
    return max(1, min(int(duration_s or 5), 30))


def _extract(output: Any) -> list[str]:
    if output is None:
        return []
    if isinstance(output, str):
        return [output]
    if isinstance(output, list):
        out = []
        for item in output:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and item.get("url") is not None:
                out.append(item["url"])
        return out
    if isinstance(output, dict):
        u = output.get("url")
        return [u] if isinstance(u, str) else []
    return []
