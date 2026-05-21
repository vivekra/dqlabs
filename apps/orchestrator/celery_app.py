"""
DigitalQ Labs — Celery Application Factory
Configures the async task queue with beat scheduling for idle workspace detection.
"""

from celery import Celery
from celery.schedules import crontab

from apps.orchestrator.config import settings

celery_app = Celery(
    "digitalq_orchestrator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# --------------------------------------------------------------------------
# Celery Configuration
# --------------------------------------------------------------------------
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend
    result_expires=3600,  # 1 hour TTL on task results

    # Worker tuning
    worker_prefetch_multiplier=1,  # Fair scheduling for long-running provision tasks
    worker_max_tasks_per_child=50,  # Restart workers periodically to prevent memory leaks
    task_acks_late=True,  # Acknowledge tasks only after completion (crash safety)
    task_reject_on_worker_lost=True,

    # Task routing
    task_default_queue="default",
    task_routes={
        "tasks.provision_workspace": {"queue": "provisioning"},
        "tasks.suspend_workspace": {"queue": "lifecycle"},
        "tasks.terminate_workspace": {"queue": "lifecycle"},
        "tasks.detect_idle_workspaces": {"queue": "monitoring"},
    },

    # Beat schedule — periodic tasks
    beat_schedule={
        "idle-workspace-detection": {
            "task": "tasks.detect_idle_workspaces",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
            "options": {"queue": "monitoring"},
        },
    },

    # Autodiscover task modules
    include=[
        "apps.orchestrator.tasks.provision",
        "apps.orchestrator.tasks.suspend",
        "apps.orchestrator.tasks.terminate",
        "apps.orchestrator.tasks.idle_monitor",
    ],
)
