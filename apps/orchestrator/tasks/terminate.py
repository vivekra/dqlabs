"""
DigitalQ Labs — Workspace Termination Celery Task
Full resource cleanup: Deployment → Service → Ingress → PVC → VolumeSnapshot → status update.
"""

import logging

from apps.orchestrator.celery_app import celery_app
from apps.orchestrator.db import get_workspace, update_workspace_status
from apps.orchestrator.k8s import workspace, service, storage, ingress

logger = logging.getLogger("digitalq-orchestrator.tasks.terminate")


@celery_app.task(
    name="tasks.terminate_workspace",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def terminate_workspace(
    self,
    workspace_id: str,
    retain_storage: bool = False,
) -> dict:
    """Permanently terminate a workspace and clean up all K8s resources.

    Execution steps:
    1. Fetch workspace metadata from database
    2. Delete Traefik IngressRoute
    3. Delete ClusterIP Service
    4. Delete Deployment (and all pod replicas)
    5. Delete VolumeSnapshots (cleanup)
    6. Optionally delete PVC (controlled by retain_storage flag)
    7. Update workspace status to 'terminated' in database

    All deletion steps are idempotent — 404 errors are silently ignored.

    Args:
        workspace_id: UUID string of the workspace to terminate.
        retain_storage: If True, keep the PVC for data recovery. Default False.

    Returns:
        Dict with workspace_id, status, and cleanup summary.
    """
    logger.info(
        "▶ Terminating workspace=%s retain_storage=%s (attempt %d/%d)",
        workspace_id,
        retain_storage,
        self.request.retries + 1,
        self.max_retries + 1,
    )

    cleanup_summary = {
        "ingress_deleted": False,
        "service_deleted": False,
        "deployment_deleted": False,
        "snapshot_deleted": False,
        "pvc_deleted": False,
    }

    try:
        # ── Step 1: Fetch workspace record ─────────────────────────────
        ws = get_workspace(workspace_id)
        if not ws:
            logger.warning("Workspace %s not found; marking as terminated.", workspace_id)
            update_workspace_status(workspace_id, "terminated")
            return {"workspace_id": workspace_id, "status": "terminated", "note": "already_gone"}

        ns = ws.get("namespace")
        if not ns:
            logger.warning("Workspace %s has no namespace; marking as terminated.", workspace_id)
            update_workspace_status(workspace_id, "terminated")
            return {"workspace_id": workspace_id, "status": "terminated", "note": "no_namespace"}

        # Derive resource names from workspace ID
        deploy_name = f"ws-{workspace_id[:8]}"
        svc_name = f"svc-ws-{workspace_id[:8]}"
        pvc_name = f"pvc-ws-{workspace_id[:8]}"
        snapshot_name = f"snap-ws-{workspace_id[:8]}"
        ingress_name = f"ir-ws-{workspace_id[:8]}"

        # ── Step 2: Delete IngressRoute ────────────────────────────────
        try:
            ingress.delete_ingress_route(ns, ingress_name)
            cleanup_summary["ingress_deleted"] = True
        except Exception as e:
            logger.warning("IngressRoute cleanup failed (non-fatal): %s", e)

        # ── Step 3: Delete Service ─────────────────────────────────────
        try:
            service.delete_service(ns, svc_name)
            cleanup_summary["service_deleted"] = True
        except Exception as e:
            logger.warning("Service cleanup failed (non-fatal): %s", e)

        # ── Step 4: Delete Deployment ──────────────────────────────────
        try:
            workspace.delete_deployment(ns, deploy_name)
            cleanup_summary["deployment_deleted"] = True
        except Exception as e:
            logger.warning("Deployment cleanup failed (non-fatal): %s", e)

        # ── Step 5: Skip VolumeSnapshot (local-path doesn't use snapshots) ─────
        # Note: We migrated from Longhorn to local-path, so no snapshots to delete.

        # ── Step 6: Conditionally delete PVC ───────────────────────────
        if not retain_storage:
            try:
                storage.delete_pvc(ns, pvc_name)
                cleanup_summary["pvc_deleted"] = True
            except Exception as e:
                logger.warning("PVC cleanup failed (non-fatal): %s", e)
        else:
            logger.info("Retaining PVC %s for data recovery.", pvc_name)

        # ── Step 7: Update DB status ──────────────────────────────────
        update_workspace_status(
            workspace_id=workspace_id,
            status="terminated",
            ingress_url=None,
        )

        result = {
            "workspace_id": workspace_id,
            "status": "terminated",
            "namespace": ns,
            "cleanup": cleanup_summary,
        }
        logger.info("✅ Workspace %s terminated. Cleanup: %s", workspace_id, cleanup_summary)
        return result

    except Exception as exc:
        logger.error(
            "❌ Terminate failed for workspace %s (attempt %d): %s",
            workspace_id,
            self.request.retries + 1,
            exc,
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))

        # Force status update on final failure
        try:
            update_workspace_status(workspace_id, "terminated")
        except Exception:
            pass

        return {
            "workspace_id": workspace_id,
            "status": "terminated",
            "error": str(exc),
            "cleanup": cleanup_summary,
        }
