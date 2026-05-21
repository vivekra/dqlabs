"""
Traefik IngressRoute builder for DigitalQ Labs workspaces.

Creates and deletes Traefik ``IngressRoute`` custom resources to expose
workspace services with TLS passthrough.
"""

import logging

from kubernetes.client.exceptions import ApiException

from .client import K8sClient

logger = logging.getLogger("digitalq.k8s.ingress")

INGRESS_PREFIX = "ir-ws-"

# Traefik IngressRoute CRD coordinates
_TRAEFIK_GROUP = "traefik.io"
_TRAEFIK_VERSION = "v1alpha1"
_TRAEFIK_PLURAL = "ingressroutes"


def _ingress_route_name(workspace_id: str) -> str:
    """Derive IngressRoute name from workspace ID."""
    return f"{INGRESS_PREFIX}{workspace_id[:8]}"


def create_ingress_route(
    workspace_id: str,
    namespace: str,
    service_name: str,
    service_port: int,
    domain_suffix: str,
) -> str:
    """Create a Traefik IngressRoute CRD for a workspace.

    Generates a host rule mapping
    ``ws-{workspace_id[:8]}.{namespace}.{domain_suffix}``
    with TLS passthrough.

    Args:
        workspace_id: Unique workspace identifier.
        namespace: Target namespace.
        service_name: Backend ClusterIP Service name.
        service_port: Backend service port number.
        domain_suffix: Base domain (e.g. ``digitalqlabs.io``).

    Returns:
        The IngressRoute resource name.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    ir_name = _ingress_route_name(workspace_id)
    hostname = f"ws-{workspace_id[:8]}.{namespace}.{domain_suffix}"

    ingress_body = {
        "apiVersion": f"{_TRAEFIK_GROUP}/{_TRAEFIK_VERSION}",
        "kind": "IngressRoute",
        "metadata": {
            "name": ir_name,
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
                "workspace-id": workspace_id,
            },
        },
        "spec": {
            "entryPoints": ["websecure"],
            "routes": [
                {
                    "match": f"Host(`{hostname}`)",
                    "kind": "Rule",
                    "services": [
                        {
                            "name": service_name,
                            "port": service_port,
                        }
                    ],
                }
            ],
            "tls": {
                "passthrough": True,
            },
        },
    }

    try:
        k8s.custom_objects.create_namespaced_custom_object(
            group=_TRAEFIK_GROUP,
            version=_TRAEFIK_VERSION,
            namespace=namespace,
            plural=_TRAEFIK_PLURAL,
            body=ingress_body,
        )
        logger.info(
            "Created IngressRoute %s (host=%s) in namespace %s.",
            ir_name,
            hostname,
            namespace,
        )
    except ApiException as exc:
        if exc.status == 409:
            logger.info(
                "IngressRoute %s already exists in namespace %s.", ir_name, namespace
            )
        else:
            logger.error(
                "Failed to create IngressRoute %s: %s %s",
                ir_name,
                exc.status,
                exc.reason,
            )
            raise

    return ir_name


def delete_ingress_route(namespace: str, ingress_name: str) -> None:
    """Delete a Traefik IngressRoute.

    Args:
        namespace: Namespace of the IngressRoute.
        ingress_name: Name of the IngressRoute resource.

    Raises:
        ApiException: On unexpected Kubernetes API errors (404 is logged and ignored).
    """
    k8s = K8sClient.get_instance()

    try:
        k8s.custom_objects.delete_namespaced_custom_object(
            group=_TRAEFIK_GROUP,
            version=_TRAEFIK_VERSION,
            namespace=namespace,
            plural=_TRAEFIK_PLURAL,
            name=ingress_name,
        )
        logger.info(
            "Deleted IngressRoute %s from namespace %s.", ingress_name, namespace
        )
    except ApiException as exc:
        if exc.status == 404:
            logger.warning(
                "IngressRoute %s not found in namespace %s; nothing to delete.",
                ingress_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to delete IngressRoute %s: %s %s",
                ingress_name,
                exc.status,
                exc.reason,
            )
            raise
