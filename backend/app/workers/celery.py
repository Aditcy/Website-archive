from celery import Celery

from ..config import cfg

cel = Celery(
    "archive",
    broker=cfg.redis,
    backend=cfg.redis,
    include=["backend.app.workers.tasks"],
)

cel.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)
