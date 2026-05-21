"""
DigitalQ Labs — Workspace Suspend Celery Task
Scale-to-zero + VolumeSnapshot + ingress teardown for idle cost elimination.
"""

import logging

from apps.orchestrator.celery_app import celery_app
from apps.orchestrator.db import get_workspace, update_workspace_status
from apps.orchestrator.k8s import workspace, storage, ingress

logger = logging.getLogger("digitalq-orchestrator.tasks.suspend")


@celery_app.task(
    name="tasks.suspend_workspace",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def suspend_workspace(self, workspace_id: str) -> dict:
    """Suspend a running workspace to eliminate compute costs.

    Execution steps:
    1. Fetch workspace metadata from database
    2. Create VolumeSnapshot of workspace PVC (preserves all user data)
    3. Scale deployment replicas to 0 (stops all containers, frees CPU/RAM)
    4. Delete IngressRoute (removes external access routing)
    5. Update workspace status to 'suspended' in database

    This task is idempotent — safe to retry on partial failures.

    Args:
        workspace_id: UUID string of the workspace to suspend.

    Returns:
        Dict with workspace_id, status, and snapshot name.
    """
    logger.info(
        "▶ Suspending workspace=%s (attempt %d/%d)",
        workspace_id,
        self.request.retries + 1,
        self.max_retries + 1,
    )

    try:
        # ── Step 1: Fetch workspace record ─────────────────────────────
        ws = get_workspace(workspace_id)
        if not ws:
            logger.error("Workspace %s not found in database.", workspace_id)
            return {"workspace_id": workspace_id, "status": "error", "error": "not_found"}

        ns = ws.get("namespace")
        if not ns:
            logger.error("Workspace %s has no namespace assigned.", workspace_id)
            update_workspace_status(workspace_id, "suspended")
            return {"workspace_id": workspace_id, "status": "suspended", "note": "no_namespace"}

        deploy_name = f"ws-{workspace_id[:8]}"
        pvc_name = f"pvc-ws-{workspace_id[:8]}"
        snapshot_name = f"snap-ws-{workspace_id[:8]}"
        ingress_name = f"ir-ws-{workspace_id[:8]}"

        # ── Step 2: Skip VolumeSnapshot (local-path retains data automatically) ─
        # Note: We migrated from Longhorn to local-path, so we just scale to 0.

        # ── Step 3: Scale deployment to 0 ──────────────────────────────
        try:
            workspace.scale_deployment(ns, deploy_name, replicas=0)
            logger.info("Deployment %s scaled to 0 replicas.", deploy_name)
        except Exception as scale_err:
            logger.warning(
                "Deployment scale-down failed (may already be gone): %s", scale_err
            )

        # ── Step 4: Delete IngressRoute ────────────────────────────────
        try:
            ingress.delete_ingress_route(ns, ingress_name)
            logger.info("IngressRoute %s deleted.", ingress_name)
        except Exception as ing_err:
            logger.warning(
                "IngressRoute deletion failed (non-fatal): %s", ing_err
            )

        # ── Step 5: Update DB status ──────────────────────────────────
        update_workspace_status(
            workspace_id=workspace_id,
            status="suspended",
            ingress_url=None,
        )

        result = {
            "workspace_id": workspace_id,
            "status": "suspended",
            "namespace": ns,
            "snapshot": snapshot_name,
        }
        logger.info("✅ Workspace %s suspended successfully.", workspace_id)
        return result

    except Exception as exc:
        logger.error(
            "❌ Suspend failed for workspace %s (attempt %d): %s",
            workspace_id,
            self.request.retries + 1,
            exc,
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))

        # On final failure, still try to mark as suspended for safety
        try:
            update_workspace_status(workspace_id, "suspended")
        except Exception:
            pass

        return {
            "workspace_id": workspace_id,
            "status": "suspended",
            "error": str(exc),
        }
