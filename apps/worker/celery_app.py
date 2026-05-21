from __future__ import annotations

from celery import Celery
from apps.api.settings import settings

celery_app = Celery(
    "genai_explainer",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["apps.worker.tasks.pipeline"],  # ensure module import
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Celery CLI compatibility for `-A apps.worker.celery_app`
app = celery_app
