"""
Workspace resource builder for DigitalQ Labs.

Creates, scales, queries, and deletes Deployment resources for
code-server + terminal-agent workspace pods.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from .client import K8sClient

logger = logging.getLogger("digitalq.k8s.workspace")

DEPLOYMENT_PREFIX = "ws-"


@dataclass(frozen=True)
class DeploymentStatus:
    """Snapshot of a workspace Deployment's readiness."""

    name: str
    namespace: str
    ready_replicas: int
    desired_replicas: int
    available: bool

    @property
    def is_ready(self) -> bool:
        """Return True when all desired replicas are ready."""
        return self.ready_replicas >= self.desired_replicas > 0


def _deployment_name(workspace_id: str) -> str:
    """Derive deployment name from workspace ID."""
    return f"{DEPLOYMENT_PREFIX}{workspace_id[:8]}"


def create_workspace_deployment(
    workspace_id: str,
    namespace: str,
    template_spec: dict,
    cpu_limit: str,
    memory_limit: str,
) -> str:
    """Create a Deployment for a workspace with code-server and terminal-agent containers.

    The deployment enforces security best practices:
    - runAsUser / runAsGroup / fsGroup 1000
    - Drop ALL capabilities
    - No privilege escalation

    Args:
        workspace_id: Unique workspace identifier.
        namespace: Target namespace.
        template_spec: Dict with keys ``tenant_id``, ``code_server_image``,
            ``terminal_agent_image``, ``cpu_request``, ``memory_request``.
        cpu_limit: CPU limit for code-server (e.g. ``"2"``).
        memory_limit: Memory limit for code-server (e.g. ``"4Gi"``).

    Returns:
        The deployment name.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    deploy_name = _deployment_name(workspace_id)
    tenant_id: str = template_spec["tenant_id"]
    code_server_image: str = template_spec.get(
        "code_server_image", "codercom/code-server:latest"
    )
    terminal_agent_image: str = template_spec.get(
        "terminal_agent_image", "digitalqlabs/terminal-agent:latest"
    )
    cpu_request: str = template_spec.get("cpu_request", "250m")
    memory_request: str = template_spec.get("memory_request", "512Mi")

    labels = {
        "app": "digitalq-workspace",
        "workspace-id": workspace_id,
        "tenant-id": tenant_id,
    }

    security_context_drop_all = client.V1SecurityContext(
        allow_privilege_escalation=False,
        capabilities=client.V1Capabilities(drop=["ALL"]),
    )

    code_server_container = client.V1Container(
        name="code-server",
        image=code_server_image,
        ports=[client.V1ContainerPort(container_port=8080, name="http")],
        resources=client.V1ResourceRequirements(
            limits={"cpu": cpu_limit, "memory": memory_limit},
            requests={"cpu": cpu_request, "memory": memory_request},
        ),
        security_context=security_context_drop_all,
        volume_mounts=[
            client.V1VolumeMount(
                name="workspace-storage",
                mount_path="/home/coder/project",
            )
        ],
        env=[
            client.V1EnvVar(name="WORKSPACE_ID", value=workspace_id),
            client.V1EnvVar(name="TENANT_ID", value=tenant_id),
        ],
    )

    terminal_agent_container = client.V1Container(
        name="terminal-agent",
        image=terminal_agent_image,
        ports=[client.V1ContainerPort(container_port=3000, name="ws")],
        resources=client.V1ResourceRequirements(
            limits={"cpu": "500m", "memory": "256Mi"},
            requests={"cpu": "100m", "memory": "64Mi"},
        ),
        security_context=client.V1SecurityContext(
            allow_privilege_escalation=False,
            read_only_root_filesystem=True,
            capabilities=client.V1Capabilities(drop=["ALL"]),
        ),
    )

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=deploy_name,
            namespace=namespace,
            labels=labels,
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={
                    "app": "digitalq-workspace",
                    "workspace-id": workspace_id,
                }
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1PodSpec(
                    security_context=client.V1PodSecurityContext(
                        run_as_user=1000,
                        run_as_group=1000,
                        fs_group=1000,
                    ),
                    containers=[code_server_container, terminal_agent_container],
                    volumes=[
                        client.V1Volume(
                            name="workspace-storage",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=f"pvc-ws-{workspace_id[:8]}"
                            ),
                        )
                    ],
                ),
            ),
        ),
    )

    try:
        k8s.apps_v1.create_namespaced_deployment(
            namespace=namespace, body=deployment
        )
        logger.info(
            "Created Deployment %s in namespace %s.", deploy_name, namespace
        )
    except ApiException as exc:
        if exc.status == 409:
            logger.info("Deployment %s already exists in namespace %s.", deploy_name, namespace)
        else:
            logger.error(
                "Failed to create Deployment %s: %s %s",
                deploy_name,
                exc.status,
                exc.reason,
            )
            raise

    return deploy_name


def scale_deployment(namespace: str, deployment_name: str, replicas: int) -> None:
    """Scale a workspace deployment (0 to suspend, 1 to resume).

    Args:
        namespace: Namespace of the deployment.
        deployment_name: Name of the deployment.
        replicas: Desired replica count.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()

    body = {"spec": {"replicas": replicas}}

    try:
        k8s.apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name, namespace=namespace, body=body
        )
        logger.info(
            "Scaled Deployment %s in namespace %s to %d replicas.",
            deployment_name,
            namespace,
            replicas,
        )
    except ApiException as exc:
        logger.error(
            "Failed to scale Deployment %s: %s %s",
            deployment_name,
            exc.status,
            exc.reason,
        )
        raise


def delete_deployment(namespace: str, deployment_name: str) -> None:
    """Delete a workspace deployment.

    Args:
        namespace: Namespace of the deployment.
        deployment_name: Name of the deployment.

    Raises:
        ApiException: On unexpected Kubernetes API errors (404 is logged and ignored).
    """
    k8s = K8sClient.get_instance()

    try:
        k8s.apps_v1.delete_namespaced_deployment(
            name=deployment_name, namespace=namespace
        )
        logger.info(
            "Deleted Deployment %s from namespace %s.", deployment_name, namespace
        )
    except ApiException as exc:
        if exc.status == 404:
            logger.warning(
                "Deployment %s not found in namespace %s; nothing to delete.",
                deployment_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to delete Deployment %s: %s %s",
                deployment_name,
                exc.status,
                exc.reason,
            )
            raise


def get_deployment_status(
    namespace: str, deployment_name: str
) -> Optional[DeploymentStatus]:
    """Return the current readiness status of a workspace deployment.

    Args:
        namespace: Namespace of the deployment.
        deployment_name: Name of the deployment.

    Returns:
        A ``DeploymentStatus`` dataclass, or ``None`` if the deployment
        does not exist.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()

    try:
        dep = k8s.apps_v1.read_namespaced_deployment(
            name=deployment_name, namespace=namespace
        )
    except ApiException as exc:
        if exc.status == 404:
            logger.info(
                "Deployment %s not found in namespace %s.", deployment_name, namespace
            )
            return None
        logger.error(
            "Failed to read Deployment %s: %s %s",
            deployment_name,
            exc.status,
            exc.reason,
        )
        raise

    ready = dep.status.ready_replicas or 0
    desired = dep.spec.replicas or 0

    status = DeploymentStatus(
        name=deployment_name,
        namespace=namespace,
        ready_replicas=ready,
        desired_replicas=desired,
        available=ready >= desired > 0,
    )
    logger.debug("Deployment %s status: %s", deployment_name, status)
    return status
