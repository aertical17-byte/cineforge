"""Mock provider — ONLY for automated tests / CI smoke (AI_MOCK_MODE=1).

It deliberately produces obviously-artificial output (a generated SVG raster) so that
mock results can never be mistaken for real model output even in a test environment.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import re
from typing import Any, Dict, Optional

from app.providers.base import (AIProvider, GenerateResult, ImageRequest,
                                ProviderNotConfigured, ProviderUnsupported, VideoRequest)

_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class MockProvider(AIProvider):
    id = "mock"

    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir

    @staticmethod
    def _svg(prompt: str, seedish: str, kind: str) -> bytes:
        h = hashlib.sha256((prompt + seedish).encode()).hexdigest()
        c1, c2 = h[:6], h[6:12]
        label = re.sub(r"[^a-zA-Z0-9 .-]", "", prompt)[:64].upper() or "CINEFORGE MOCK"
        head = f"MOCK {kind.upper()}"
        svg = (
            f"<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512'>"
            f"<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
            f"<stop offset='0' stop-color='#{c1}'/><stop offset='1' stop-color='#{c2}'/></linearGradient></defs>"
            f"<rect width='512' height='512' fill='url(#g)'/>"
            f"<text x='24' y='40' fill='white' font-family='monospace' font-size='20'>{head}</text>"
            f"<text x='24' y='480' fill='white' font-family='monospace' font-size='14'>{label}</text>"
            f"</svg>"
        ).encode("utf-8")
        return svg

    async def generate_image(self, req: ImageRequest) -> GenerateResult:
        data = self._svg(req.prompt, f"{req.seed or ''}", "image")
        url = _temp_uri(data)
        return GenerateResult(kind="image", urls=[url] * max(1, req.batch or 1),
                              provider_job_ref="mock-image")

    async def generate_video(self, req: VideoRequest) -> GenerateResult:
        data = self._svg(req.prompt, f"{req.seed or ''}", "video")
        url = _temp_uri(data)
        return GenerateResult(kind="video", urls=[url], provider_job_ref="mock-video",
                              native_metadata={"duration_s": req.duration_s, "note": "mock"})
    async def upscale_image(self, url: str, scale: int = 2) -> GenerateResult:
        return GenerateResult(kind="image", urls=[_temp_uri(_PNG_1PX)], provider_job_ref="mock-upscale")

    async def download(self, urls):  # decode the temp URIs directly
        return DownloadedLike(urls)


class DownloadedLike:
    def __init__(self, urls):
        self.items = [base64.b64decode(u.split(",", 1)[1]) for u in urls]
        self.mimes = ["image/svg+xml"]


def _temp_uri(data: bytes) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode()


def get_mock_provider_if_allowed(settings) -> Optional[MockProvider]:
    if not settings.AI_MOCK_MODE:
        raise ProviderNotConfigured(
            "mock provider requires AI_MOCK_MODE=1 and is forbidden outside automated tests"
        )
    return MockProvider(settings.storage_local_dir)
