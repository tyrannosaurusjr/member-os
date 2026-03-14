from celery import Celery

from app.config import settings

celery_app = Celery(
    "member_os",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "stripe-inbound-hourly": {
            "task": "app.workers.tasks.run_connector_pull",
            "schedule": 3600.0,
            "kwargs": {"source_system": "stripe", "full_refresh": False},
        },
        "mailchimp-inbound-hourly": {
            "task": "app.workers.tasks.run_connector_pull",
            "schedule": 3600.0,
            "kwargs": {"source_system": "mailchimp", "full_refresh": False},
        },
        "luma-inbound-hourly": {
            "task": "app.workers.tasks.run_connector_pull",
            "schedule": 3600.0,
            "kwargs": {"source_system": "luma", "full_refresh": False},
        },
        "identity-resolution-daily": {
            "task": "app.workers.tasks.run_identity_resolution",
            "schedule": 86400.0,
            "kwargs": {"person_ids": None},
        },
    },
)
