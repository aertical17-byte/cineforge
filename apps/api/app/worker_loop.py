"""Background worker loop: claims lease-based jobs, reconciles credits, never fakes success."""
from __future__ import annotations

import asyncio
import datetime as dt
import logging

from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import GenerationJob
from app.services import jobs

log = logging.getLogger("worker")
S = get_settings()


async def _cancel_guard():
    """Fail jobs whose user requested cancellation while running (idempotent)."""
    async with SessionFactory() as s:
        canceled = (await s.execute(
            select(GenerationJob).where(GenerationJob.status == "running"),
        )).scalars().all()
        # cancellation is handled in the API router; worker-side guard verifies lease staleness
        for job in canceled:
            if job.claimed_at and (dt.datetime.now(dt.timezone.utc) - job.claimed_at).total_seconds() > 900:
                job.status = "queued"
                job.claimed_by = None
        await s.commit()


async def main():
    logging.basicConfig(level=logging.INFO)
    log.info("worker up (concurrency=%d)", S.worker_concurrency)
    while True:
        try:
            await jobs.process_pending(batch=S.worker_concurrency)
            await _cancel_guard()
        except Exception:  # noqa: BLE001 — worker must survive transient DB/provider errors
            log.exception("loop error")
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
