"""
DigitalQ Labs — Idle Workspace Detection Celery Beat Task
Periodically scans running workspaces and auto-suspends those exceeding the idle threshold.
"""

import logging

from apps.orchestrator.celery_app import celery_app
from apps.orchestrator.config import settings
from apps.orchestrator.db import get_idle_workspaces

logger = logging.getLogger("digitalq-orchestrator.tasks.idle_monitor")


@celery_app.task(
    name="tasks.detect_idle_workspaces",
    acks_late=True,
)
def detect_idle_workspaces() -> dict:
    """Scan for idle running workspaces and dispatch suspend tasks.

    Queries the database for workspaces with status='running' whose
    last_active_at timestamp exceeds IDLE_TIMEOUT_MINUTES. For each
    idle workspace, dispatches a suspend_workspace task.

    This task runs on a Celery beat schedule (default: every 5 minutes).

    Returns:
        Dict with count of idle workspaces found and suspended.
    """
    idle_minutes = settings.IDLE_TIMEOUT_MINUTES
    logger.info(
        "🔍 Scanning for idle workspaces (threshold: %d minutes)...",
        idle_minutes,
    )

    try:
        idle_workspaces = get_idle_workspaces(idle_minutes)

        if not idle_workspaces:
            logger.info("No idle workspaces found.")
            return {"idle_count": 0, "suspended": []}

        suspended_ids = []
        for ws in idle_workspaces:
            ws_id = str(ws["id"])
            logger.info(
                "Workspace %s idle since %s — dispatching suspend.",
                ws_id,
                ws.get("last_active_at"),
            )
            celery_app.send_task(
                "tasks.suspend_workspace",
                args=[ws_id],
                queue="lifecycle",
            )
            suspended_ids.append(ws_id)

        logger.info(
            "✅ Idle scan complete: %d workspace(s) queued for suspension.",
            len(suspended_ids),
        )
        return {
            "idle_count": len(idle_workspaces),
            "suspended": suspended_ids,
        }

    except Exception as exc:
        logger.error(
            "❌ Idle detection scan failed: %s",
            exc,
            exc_info=True,
        )
        return {"idle_count": 0, "error": str(exc)}
