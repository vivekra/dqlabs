"""
DigitalQ Labs — Orchestrator Entrypoint
Celery worker and beat scheduler for workspace lifecycle management.

Usage:
    # Start worker (processes provisioning and lifecycle queues):
    celery -A apps.orchestrator.main:celery_app worker \
        --queues=default,provisioning,lifecycle,monitoring \
        --loglevel=info --concurrency=4

    # Start beat scheduler (dispatches periodic idle detection):
    celery -A apps.orchestrator.main:celery_app beat \
        --loglevel=info

    # Start combined worker + beat (development only):
    celery -A apps.orchestrator.main:celery_app worker --beat \
        --queues=default,provisioning,lifecycle,monitoring \
        --loglevel=info --concurrency=4
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Import the configured Celery app — this is what Celery discovers
from apps.orchestrator.celery_app import celery_app  # noqa: E402, F401

# Ensure all tasks are registered via import side-effects
import apps.orchestrator.tasks  # noqa: E402, F401

logger = logging.getLogger("digitalq-orchestrator")
logger.info("DigitalQ Labs Orchestrator loaded. Celery app: %s", celery_app.main)
