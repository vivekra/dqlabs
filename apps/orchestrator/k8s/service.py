"""
Service builder for DigitalQ Labs workspaces.

Creates and deletes ClusterIP Services that front workspace pods.
"""

import logging
from typing import List

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from .client import K8sClient

logger = logging.getLogger("digitalq.k8s.service")

SERVICE_PREFIX = "svc-ws-"


def _service_name(workspace_id: str) -> str:
    """Derive Service name from workspace ID."""
    return f"{SERVICE_PREFIX}{workspace_id[:8]}"


def create_workspace_service(
    workspace_id: str,
    namespace: str,
    ports: List[dict],
) -> str:
    """Create a ClusterIP Service selecting workspace pods.

    Args:
        workspace_id: Unique workspace identifier.
        namespace: Target namespace.
        ports: List of port dicts, each containing ``name``, ``port``,
            and ``target_port`` keys. Example::

                [
                    {"name": "http", "port": 8080, "target_port": 8080},
                    {"name": "ws", "port": 3000, "target_port": 3000},
                ]

    Returns:
        The Service name.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    svc_name = _service_name(workspace_id)

    service_ports = [
        client.V1ServicePort(
            name=p["name"],
            port=p["port"],
            target_port=p.get("target_port", p["port"]),
            protocol=p.get("protocol", "TCP"),
        )
        for p in ports
    ]

    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=svc_name,
            namespace=namespace,
            labels={
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
                "workspace-id": workspace_id,
            },
        ),
        spec=client.V1ServiceSpec(
            type="ClusterIP",
            selector={
                "app": "digitalq-workspace",
                "workspace-id": workspace_id,
            },
            ports=service_ports,
        ),
    )

    try:
        k8s.core_v1.create_namespaced_service(namespace=namespace, body=service)
        logger.info(
            "Created Service %s in namespace %s with %d port(s).",
            svc_name,
            namespace,
            len(ports),
        )
    except ApiException as exc:
        if exc.status == 409:
            logger.info(
                "Service %s already exists in namespace %s.", svc_name, namespace
            )
        else:
            logger.error(
                "Failed to create Service %s: %s %s",
                svc_name,
                exc.status,
                exc.reason,
            )
            raise

    return svc_name


def delete_service(namespace: str, service_name: str) -> None:
    """Delete a workspace Service.

    Args:
        namespace: Namespace of the Service.
        service_name: Name of the Service.

    Raises:
        ApiException: On unexpected Kubernetes API errors (404 is logged and ignored).
    """
    k8s = K8sClient.get_instance()

    try:
        k8s.core_v1.delete_namespaced_service(
            name=service_name, namespace=namespace
        )
        logger.info("Deleted Service %s from namespace %s.", service_name, namespace)
    except ApiException as exc:
        if exc.status == 404:
            logger.warning(
                "Service %s not found in namespace %s; nothing to delete.",
                service_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to delete Service %s: %s %s",
                service_name,
                exc.status,
                exc.reason,
            )
            raise
