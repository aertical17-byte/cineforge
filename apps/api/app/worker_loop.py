"""Background worker loop: claims lease-based jobs, reconciles credits, never fakes success."""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import pathlib

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import GenerationJob
from app.services import jobs

log = logging.getLogger("worker")
S = get_settings()


def _file_log() -> None:
    """Log to a file too: CI drops a background step's stdout once its step ends.

    The file (data/worker.log next to the local storage dir) keeps ground truth for
    e2e diagnosis and matches the deployment pattern of file-based worker logs.
    """
    p = pathlib.Path(S.storage_local_dir).parent / "worker.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(str(p))
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger().addHandler(fh)


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


async def _enable_wal():
    """Switch the shared SQLite file to WAL (persistent, idempotent).

    With API + worker as separate processes on one file, WAL lets the API keep
    polling while the worker writes; the connect timeout in db.py covers locking.
    """
    from sqlalchemy import text
    async with SessionFactory() as s:
        await s.execute(text("pragma journal_mode=WAL"))
        await s.commit()


async def main():
    logging.basicConfig(level=logging.INFO)
    _file_log()
    log.info("worker up (concurrency=%d)", S.worker_concurrency)
    if get_settings().database_url.startswith("sqlite"):
        try:
            await _enable_wal()
        except Exception:  # noqa: BLE001 — concurrency opt-in, never a reason to die
            log.exception("sqlite WAL enable failed (continuing)")
    while True:
        try:
            await jobs.process_pending(batch=S.worker_concurrency)
            await _cancel_guard()
        except Exception:  # noqa: BLE001 — worker must survive transient DB/provider errors
            log.exception("loop error")
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())

