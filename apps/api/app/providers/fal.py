"""fal.ai adapter (per fal.ai's public queue API docs).

- Submit:  POST https://queue.fal.run/{model_id}
- Status:  GET  https://queue.fal.run/{requests_id}/status
- Result:  GET  https://queue.fal.run/{requests_id}
Auth: "Key" scheme with the fal key.

This structure mirrors fal's published queue endpoints; `scripts/verify_providers.py`
runs a live check when a key is present and ProviderRegistryStatus records the verification.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.providers.base import (AIProvider, GenerateResult, ImageRequest, JobState,
                                ProviderError, ProviderNotConfigured, VideoRequest,
                                poll_until)

IMAGE_SIZE = {"1:1": "1024x1024", "16:9": "1344x768", "9:16": "768x1344", "4:3": "1120x832", "3:4": "832x1120"}
CAMERA_TO_KLING = {
    "pan_left": {"direction": "left"}, "pan_right": {"direction": "right"},
    "tilt_up": {"direction": "up"}, "tilt_down": {"direction": "down"},
    "zoom_in": {"direction": "zoom_in"}, "zoom_out": {"direction": "zoom_out"},
}


class FalProvider(AIProvider):
    id = "fal"
    base = "https://queue.fal.run"

    def __init__(self, key: Optional[str]):
        self.key = key
        if not key:
            raise ProviderNotConfigured(self.id)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Key {self.key}", "Content-Type": "application/json"}

    async def _enqueue(self, model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{self.base}/{model_id}", json=payload, headers=self._headers())
            if r.status_code >= 500:
                raise ProviderError(f"fal server error {r.status_code}")
            r.raise_for_status()
            return r.json()

    async def _status(self, model_id: str, request_id: str) -> JobState:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{self.base}/{model_id}/requests/{request_id}/status",
                                 headers=self._headers())
            r.raise_for_status()
            s = r.json().get("status")
            return {"IN_QUEUE": JobState.running, "IN_PROGRESS": JobState.running,
                    "COMPLETED": JobState.succeeded}.get(s, JobState.failed)

    async def _result(self, model_id: str, request_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{self.base}/{model_id}/requests/{request_id}",
                                 headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def _await(self, model_id: str, request_id: str) -> GenerateResult:
        async def step():
            state = await self._status(model_id, request_id)
            if state == JobState.succeeded:
                data = await self._result(model_id, request_id)
                urls = _extract_fal_urls(data)
                if not urls:
                    raise ProviderError("fal completed without output urls")
                return state, urls, data
            if state == JobState.failed:
                async with httpx.AsyncClient(timeout=60) as client:
                    r = await client.get(f"{self.base}/{model_id}/requests/{request_id}/status",
                                         headers=self._headers())
                    try:
                        detail = r.json().get("error", "")
                    except Exception:
                        detail = ""
                    raise ProviderError(f"fal failed: {detail}")
            return state, None, {}

        state, urls, meta = await poll_until(step, interval_s=3.0)
        return GenerateResult(kind="media", urls=urls or [], provider_job_ref=request_id,
                              native_metadata={"fal": meta})

    async def generate_image(self, req: ImageRequest) -> GenerateResult:
        payload = {
            "prompt": req.prompt,
            "image_size": IMAGE_SIZE.get(req.aspect_ratio, "1024x1024"),
            "num_images": max(1, req.batch or 1),
        }
        if req.negative_prompt and (req.provider_config or {}).get("accepts_negative", True):
            payload["negative_prompt"] = req.negative_prompt
        if req.seed is not None:
            payload["seed"] = int(req.seed)
        if req.reference_urls:
            payload[(req.provider_config or {}).get("reference_key", "image_url")] = req.reference_urls[0]
        payload.update((req.provider_config or {}).get("extra_input", {}) or {})
        sub = await self._enqueue(req.provider_model.replace("/", "/"), payload)
        return await self._await(req.provider_model, sub["request_id"])

    async def generate_video(self, req: VideoRequest) -> GenerateResult:
        payload: Dict[str, Any] = {"prompt": req.prompt, "duration": int(req.duration_s or 5)}
        if req.first_frame_url:
            payload["image_url"] = req.first_frame_url
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt
        if req.camera_control and "camera" in (req.provider_config or {}).get("structured_params", []):
            cc = CAMERA_TO_KLING.get(req.camera_control.get("move"))
            if cc:
                payload["camera"] = cc
        payload.update((req.provider_config or {}).get("extra_input", {}) or {})
        sub = await self._enqueue(req.provider_model, payload)
        return await self._await(req.provider_model, sub["request_id"])

    async def cancel(self, ref: str) -> JobState:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.delete(f"{self.base}/requests/{ref}")
            return JobState.canceled if r.status_code < 400 else JobState.running


def _extract_fal_urls(data: Dict[str, Any]) -> list[str]:
    urls: list[str] = []

    def walk(node: Any):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and (k.endswith("url") or k.startswith("image_") or k.endswith("_uri")) and v.startswith(("http",)):
                    urls.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data.get("images") or data.get("videos") or data.get("output") or data)
    # de-dup, keep order
    seen = set()
    return [u for u in urls if not (u in seen or seen.add(u))]
