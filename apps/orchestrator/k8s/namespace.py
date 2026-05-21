"""
Namespace provisioner for DigitalQ Labs tenant isolation.

Handles namespace lifecycle, resource quotas, and default-deny
network policies with Traefik ingress exceptions.
"""

import logging

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from .client import K8sClient

logger = logging.getLogger("digitalq.k8s.namespace")

NAMESPACE_PREFIX = "dq-"


def _namespace_name(tenant_id: str) -> str:
    """Derive the Kubernetes namespace name from a tenant ID.

    Args:
        tenant_id: Full tenant identifier.

    Returns:
        Namespace name in the form ``dq-{tenant_id[:8]}``.
    """
    return f"{NAMESPACE_PREFIX}{tenant_id[:8]}"


def ensure_namespace(tenant_id: str) -> str:
    """Create the tenant namespace if it does not already exist.

    Args:
        tenant_id: Full tenant identifier.

    Returns:
        The namespace name that was ensured.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    ns_name = _namespace_name(tenant_id)

    body = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=ns_name,
            labels={
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
                "digitalq.io/tenant-id": tenant_id,
            },
        )
    )

    try:
        k8s.core_v1.create_namespace(body=body)
        logger.info("Created namespace %s for tenant %s.", ns_name, tenant_id)
    except ApiException as exc:
        if exc.status == 409:
            logger.info("Namespace %s already exists.", ns_name)
        else:
            logger.error(
                "Failed to create namespace %s: %s %s",
                ns_name,
                exc.status,
                exc.reason,
            )
            raise

    return ns_name


def apply_resource_quota(
    namespace: str,
    cpu: str,
    memory: str,
    storage: str,
    pods: int,
) -> None:
    """Create or update a ResourceQuota in the given namespace.

    Args:
        namespace: Target namespace.
        cpu: CPU limit (e.g. ``"4"``).
        memory: Memory limit (e.g. ``"8Gi"``).
        storage: Storage limit (e.g. ``"50Gi"``).
        pods: Maximum number of pods.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    quota_name = f"{namespace}-quota"

    quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(
            name=quota_name,
            namespace=namespace,
            labels={
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
            },
        ),
        spec=client.V1ResourceQuotaSpec(
            hard={
                "limits.cpu": cpu,
                "limits.memory": memory,
                "requests.storage": storage,
                "pods": str(pods),
            }
        ),
    )

    try:
        k8s.core_v1.create_namespaced_resource_quota(
            namespace=namespace, body=quota
        )
        logger.info("Created ResourceQuota %s in namespace %s.", quota_name, namespace)
    except ApiException as exc:
        if exc.status == 409:
            k8s.core_v1.replace_namespaced_resource_quota(
                name=quota_name, namespace=namespace, body=quota
            )
            logger.info(
                "Updated existing ResourceQuota %s in namespace %s.",
                quota_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to apply ResourceQuota %s: %s %s",
                quota_name,
                exc.status,
                exc.reason,
            )
            raise


def apply_network_policy(namespace: str) -> None:
    """Apply a default-deny ingress NetworkPolicy with Traefik exceptions.

    The policy denies all ingress traffic except from pods in the
    ``traefik`` namespace (identified by namespace selector).

    Args:
        namespace: Target namespace.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    policy_name = f"{namespace}-default-deny"

    network_policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(
            name=policy_name,
            namespace=namespace,
            labels={
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
            },
        ),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(match_labels={}),
            policy_types=["Ingress"],
            ingress=[
                client.V1NetworkPolicyIngressRule(
                    _from=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={
                                    "kubernetes.io/metadata.name": "traefik",
                                }
                            )
                        )
                    ]
                )
            ],
        ),
    )

    try:
        k8s.networking_v1.create_namespaced_network_policy(
            namespace=namespace, body=network_policy
        )
        logger.info(
            "Created NetworkPolicy %s in namespace %s.", policy_name, namespace
        )
    except ApiException as exc:
        if exc.status == 409:
            k8s.networking_v1.replace_namespaced_network_policy(
                name=policy_name, namespace=namespace, body=network_policy
            )
            logger.info(
                "Updated existing NetworkPolicy %s in namespace %s.",
                policy_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to apply NetworkPolicy %s: %s %s",
                policy_name,
                exc.status,
                exc.reason,
            )
            raise


def delete_namespace(namespace: str) -> None:
    """Delete a namespace and all its resources.

    Args:
        namespace: Namespace to delete.

    Raises:
        ApiException: On unexpected Kubernetes API errors (404 is logged and ignored).
    """
    k8s = K8sClient.get_instance()

    try:
        k8s.core_v1.delete_namespace(name=namespace)
        logger.info("Deleted namespace %s.", namespace)
    except ApiException as exc:
        if exc.status == 404:
            logger.warning("Namespace %s not found; nothing to delete.", namespace)
        else:
            logger.error(
                "Failed to delete namespace %s: %s %s",
                namespace,
                exc.status,
                exc.reason,
            )
            raise
