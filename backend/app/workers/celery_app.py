"""
Celery app instance — broker/backend Redis (ADR-002).

Çalıştırma:
    cd backend
    .venv/bin/celery -A app.workers.celery_app worker --beat -l info
"""
from celery import Celery

from app.core.config import settings
from app.workers.schedules import beat_schedule

celery_app = Celery(
    "melon_kar",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,             # task fail olursa requeue
    worker_prefetch_multiplier=1,    # uzun task'lar için fair scheduling
    beat_schedule=beat_schedule,
)
