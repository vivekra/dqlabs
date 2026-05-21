"""
DigitalQ Labs — Workspace Provisioning Celery Task
Full lifecycle: namespace → ResourceQuota → NetworkPolicy → PVC → Deployment → Service → Ingress → status update.
"""

import logging
import time

from apps.orchestrator.celery_app import celery_app
from apps.orchestrator.config import settings
from apps.orchestrator.db import (
    get_tenant_quota,
    get_workspace_with_template,
    update_workspace_status,
)
from apps.orchestrator.k8s import namespace, workspace, service, storage, ingress

logger = logging.getLogger("digitalq-orchestrator.tasks.provision")


@celery_app.task(
    name="tasks.provision_workspace",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def provision_workspace(self, workspace_id: str, tenant_id: str) -> dict:
    """Provision a complete workspace environment on the K3s runtime cluster.

    Execution steps:
    1. Fetch workspace + template metadata from database
    2. Ensure tenant namespace exists with labels
    3. Apply ResourceQuota limits from tenant quota table
    4. Apply default-deny NetworkPolicy with Traefik exception
    5. Create PersistentVolumeClaim for workspace storage
    6. Create multi-container Deployment (code-server + terminal-agent)
    7. Create ClusterIP Service fronting workspace pods
    8. Create Traefik IngressRoute for external access
    9. Poll for deployment readiness (up to PROVISION_TIMEOUT_SECONDS)
    10. Update workspace status to 'running' with ingress URL

    Args:
        workspace_id: UUID string of the workspace to provision.
        tenant_id: UUID string of the owning tenant.

    Returns:
        Dict with workspace_id, status, ingress_url, and pod_name.
    """
    logger.info(
        "▶ Starting provision for workspace=%s tenant=%s (attempt %d/%d)",
        workspace_id,
        tenant_id,
        self.request.retries + 1,
        self.max_retries + 1,
    )

    try:
        # ── Step 1: Fetch workspace + template from DB ─────────────────
        ws = get_workspace_with_template(workspace_id)
        if not ws:
            logger.error("Workspace %s not found in database.", workspace_id)
            update_workspace_status(workspace_id, "failed")
            return {"workspace_id": workspace_id, "status": "failed", "error": "not_found"}

        # ── Step 2: Ensure tenant namespace ────────────────────────────
        ns_name = namespace.ensure_namespace(tenant_id)
        logger.info("Namespace ensured: %s", ns_name)

        # ── Step 3: Apply ResourceQuota ────────────────────────────────
        quota = get_tenant_quota(tenant_id)
        if quota:
            namespace.apply_resource_quota(
                namespace=ns_name,
                cpu=str(quota["max_cpus"]),
                memory=f"{quota['max_ram_mb']}Mi",
                storage=f"{quota['max_storage_gb']}Gi",
                pods=quota["max_workspaces"] * 2,  # 2 containers per workspace pod
            )
            logger.info("ResourceQuota applied to %s", ns_name)
        else:
            logger.warning("No quota found for tenant %s; skipping ResourceQuota.", tenant_id)

        # ── Step 4: Apply NetworkPolicy ────────────────────────────────
        namespace.apply_network_policy(ns_name)
        logger.info("NetworkPolicy applied to %s", ns_name)

        # ── Step 5: Create PVC ─────────────────────────────────────────
        storage_gb = int(ws.get("allocated_storage_gb", 10))
        pvc_name = storage.create_pvc(
            workspace_id=workspace_id,
            namespace=ns_name,
            storage_gb=storage_gb,
            storage_class=settings.STORAGE_CLASS,
        )
        logger.info("PVC created: %s (%dGi)", pvc_name, storage_gb)

        # ── Step 6: Create Deployment ──────────────────────────────────
        cpu_limit = str(ws.get("allocated_cpu", 1.0))
        memory_limit = f"{ws.get('allocated_ram_mb', 2048)}Mi"

        # Build template_spec for the workspace builder
        template_spec = {
            "tenant_id": tenant_id,
            "code_server_image": settings.CODE_SERVER_IMAGE,
            "terminal_agent_image": settings.TERMINAL_AGENT_IMAGE,
            "cpu_request": "250m",
            "memory_request": "512Mi",
        }

        # Merge manifest_spec from lab template if available
        manifest = ws.get("template_manifest_spec")
        if manifest and isinstance(manifest, dict):
            if "image" in manifest:
                template_spec["code_server_image"] = manifest["image"]

        deploy_name = workspace.create_workspace_deployment(
            workspace_id=workspace_id,
            namespace=ns_name,
            template_spec=template_spec,
            cpu_limit=cpu_limit,
            memory_limit=memory_limit,
        )
        logger.info("Deployment created: %s", deploy_name)

        # ── Step 7: Create Service ─────────────────────────────────────
        service_ports = [
            {"name": "http", "port": 8080, "target_port": 8080},
            {"name": "ws", "port": 3000, "target_port": 3000},
        ]
        svc_name = service.create_workspace_service(
            workspace_id=workspace_id,
            namespace=ns_name,
            ports=service_ports,
        )
        logger.info("Service created: %s", svc_name)

        # ── Step 8: Create IngressRoute ────────────────────────────────
        ingress_name = ingress.create_ingress_route(
            workspace_id=workspace_id,
            namespace=ns_name,
            service_name=svc_name,
            service_port=8080,
            domain_suffix=settings.INGRESS_DOMAIN_SUFFIX,
        )
        ingress_url = f"https://ws-{workspace_id[:8]}.{ns_name}.{settings.INGRESS_DOMAIN_SUFFIX}"
        logger.info("IngressRoute created: %s → %s", ingress_name, ingress_url)

        # ── Step 9: Wait for deployment readiness ──────────────────────
        pod_name = deploy_name  # Use deployment name as pod identifier
        deadline = time.time() + settings.PROVISION_TIMEOUT_SECONDS
        ready = False

        while time.time() < deadline:
            status = workspace.get_deployment_status(ns_name, deploy_name)
            if status and status.is_ready:
                ready = True
                logger.info("Deployment %s is ready.", deploy_name)
                break
            time.sleep(settings.PROVISION_POLL_INTERVAL)

        if not ready:
            logger.warning(
                "Deployment %s did not become ready within %ds. Marking as running anyway.",
                deploy_name,
                settings.PROVISION_TIMEOUT_SECONDS,
            )

        # ── Step 10: Update DB status ──────────────────────────────────
        update_workspace_status(
            workspace_id=workspace_id,
            status="running",
            pod_name=pod_name,
            namespace=ns_name,
            ingress_url=ingress_url,
        )

        result = {
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "status": "running",
            "namespace": ns_name,
            "pod_name": pod_name,
            "ingress_url": ingress_url,
            "deployment": deploy_name,
            "service": svc_name,
            "pvc": pvc_name,
            "ingress_route": ingress_name,
        }
        logger.info("✅ Workspace %s provisioned successfully: %s", workspace_id, ingress_url)
        return result

    except Exception as exc:
        logger.error(
            "❌ Provision failed for workspace %s (attempt %d): %s",
            workspace_id,
            self.request.retries + 1,
            exc,
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))

        # Final failure — mark workspace as failed
        update_workspace_status(workspace_id, "failed")
        return {
            "workspace_id": workspace_id,
            "status": "failed",
            "error": str(exc),
        }
