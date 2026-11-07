"""Provider interface + result types. Every adapter implements these methods."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional


class ProviderError(Exception):
    """Predictable provider-side failure (mapped to job failure + refund)."""


class ProviderNotConfigured(ProviderError):
    def __init__(self, provider_id: str):
        super().__init__(
            f"provider '{provider_id}' is not configured on this deployment: missing API key"
        )
        self.provider_id = provider_id


class ProviderUnsupported(ProviderError):
    """The requested capability is not supported by this provider/model."""


class JobState(str, Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


@dataclass
class ImageRequest:
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "1:1"
    resolution: Optional[str] = None
    seed: Optional[int] = None
    steps: Optional[int] = None
    guidance: Optional[float] = None
    batch: int = 1
    reference_urls: List[str] = field(default_factory=list)
    reference_strength: Optional[float] = None
    provider_model: str = ""
    provider_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoRequest:
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "16:9"
    duration_s: int = 5
    seed: Optional[int] = None
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None
    reference_urls: List[str] = field(default_factory=list)
    camera_control: Optional[Dict[str, Any]] = None  # structured provider params when supported
    resolution: Optional[str] = None
    provider_model: str = ""
    provider_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerateResult:
    """Provider output, already resolved to concrete media locations."""
    kind: str  # image|video
    urls: List[str]        # original provider-hosted urls (transient)
    provider_job_ref: Optional[str] = None
    native_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Handle:
    provider_job_ref: str


@dataclass
class Downloaded:
    """Bytes fetched from provider URLs during the import step."""
    items: List[bytes]
    mimes: List[str]


class AIProvider:
    """Abstract base. All methods are hot unless the capability is unsupported ⇒ raise ProviderUnsupported."""

    id: str = "abstract"

    async def generate_image(self, req: ImageRequest) -> GenerateResult:  # pragma: no cover
        raise ProviderUnsupported(self.id)

    async def generate_video(self, req: VideoRequest) -> GenerateResult:  # pragma: no cover
        raise ProviderUnsupported(self.id)

    async def upscale_image(self, url: str, scale: int = 2) -> GenerateResult:  # pragma: no cover
        raise ProviderUnsupported(self.id)

    async def cancel(self, ref: str) -> JobState:  # pragma: no cover
        raise ProviderUnsupported(self.id)

    async def download(self, urls: List[str]) -> Downloaded:
        import httpx

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            items: List[bytes] = []
            mimes: List[str] = []
            from itertools import cycle

            for u in urls:
                r = await client.get(u)
                r.raise_for_status()
                items.append(r.content)
                mimes.append(r.headers.get("content-type", "application/octet-stream"))
            return Downloaded(items=items, mimes=mimes)


async def poll_until(
    fn: Callable[[], Awaitable[tuple[JobState, Optional[GenerateResult], Dict[str, Any]]]],
    interval_s: float = 3.0,
    max_seconds: float = 900.0,
) -> tuple[JobState, Optional[GenerateResult], Dict[str, Any]]:
    """Shared polling helper (tenacity-free simple loop honoring timeouts)."""
    waited = 0.0
    while True:
        state, result, meta = await fn()
        if state != JobState.running:
            return state, result, meta
        if waited >= max_seconds:
            raise ProviderError(f"provider polling exceeded {max_seconds:.0f}s")
        await asyncio.sleep(interval_s)
        waited += interval_s
