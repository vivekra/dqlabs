"""
Persistent storage operations for DigitalQ Labs workspaces.

Manages PersistentVolumeClaims and VolumeSnapshots (via the
``snapshot.storage.k8s.io/v1`` custom resource API).
"""

import logging

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from .client import K8sClient

logger = logging.getLogger("digitalq.k8s.storage")

PVC_PREFIX = "pvc-ws-"

# VolumeSnapshot CRD coordinates
_SNAPSHOT_GROUP = "snapshot.storage.k8s.io"
_SNAPSHOT_VERSION = "v1"
_SNAPSHOT_PLURAL = "volumesnapshots"


def _pvc_name(workspace_id: str) -> str:
    """Derive PVC name from workspace ID."""
    return f"{PVC_PREFIX}{workspace_id[:8]}"


def create_pvc(
    workspace_id: str,
    namespace: str,
    storage_gb: int,
    storage_class: str = "longhorn",
) -> str:
    """Create a PersistentVolumeClaim for a workspace.

    Args:
        workspace_id: Unique workspace identifier.
        namespace: Target namespace.
        storage_gb: Requested storage size in gigabytes.
        storage_class: StorageClass name (default: ``longhorn``).

    Returns:
        The PVC name.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()
    pvc_name = _pvc_name(workspace_id)

    pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(
            name=pvc_name,
            namespace=namespace,
            labels={
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
                "workspace-id": workspace_id,
            },
        ),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            storage_class_name=storage_class,
            resources=client.V1VolumeResourceRequirements(
                requests={"storage": f"{storage_gb}Gi"},
            ),
        ),
    )

    try:
        k8s.core_v1.create_namespaced_persistent_volume_claim(
            namespace=namespace, body=pvc
        )
        logger.info(
            "Created PVC %s (%dGi, class=%s) in namespace %s.",
            pvc_name,
            storage_gb,
            storage_class,
            namespace,
        )
    except ApiException as exc:
        if exc.status == 409:
            logger.info("PVC %s already exists in namespace %s.", pvc_name, namespace)
        else:
            logger.error(
                "Failed to create PVC %s: %s %s", pvc_name, exc.status, exc.reason
            )
            raise

    return pvc_name


def delete_pvc(namespace: str, pvc_name: str) -> None:
    """Delete a PersistentVolumeClaim.

    Args:
        namespace: Namespace of the PVC.
        pvc_name: Name of the PVC.

    Raises:
        ApiException: On unexpected Kubernetes API errors (404 is logged and ignored).
    """
    k8s = K8sClient.get_instance()

    try:
        k8s.core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
        logger.info("Deleted PVC %s from namespace %s.", pvc_name, namespace)
    except ApiException as exc:
        if exc.status == 404:
            logger.warning(
                "PVC %s not found in namespace %s; nothing to delete.",
                pvc_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to delete PVC %s: %s %s", pvc_name, exc.status, exc.reason
            )
            raise


def create_volume_snapshot(
    namespace: str,
    pvc_name: str,
    snapshot_name: str,
) -> str:
    """Create a VolumeSnapshot for a PVC.

    Uses the ``snapshot.storage.k8s.io/v1`` custom resource API.

    Args:
        namespace: Namespace containing the PVC.
        pvc_name: Name of the source PVC.
        snapshot_name: Desired snapshot resource name.

    Returns:
        The snapshot name.

    Raises:
        ApiException: On unexpected Kubernetes API errors.
    """
    k8s = K8sClient.get_instance()

    snapshot_body = {
        "apiVersion": f"{_SNAPSHOT_GROUP}/{_SNAPSHOT_VERSION}",
        "kind": "VolumeSnapshot",
        "metadata": {
            "name": snapshot_name,
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "digitalq-orchestrator",
                "source-pvc": pvc_name,
            },
        },
        "spec": {
            "source": {
                "persistentVolumeClaimName": pvc_name,
            },
        },
    }

    try:
        k8s.custom_objects.create_namespaced_custom_object(
            group=_SNAPSHOT_GROUP,
            version=_SNAPSHOT_VERSION,
            namespace=namespace,
            plural=_SNAPSHOT_PLURAL,
            body=snapshot_body,
        )
        logger.info(
            "Created VolumeSnapshot %s from PVC %s in namespace %s.",
            snapshot_name,
            pvc_name,
            namespace,
        )
    except ApiException as exc:
        if exc.status == 409:
            logger.info(
                "VolumeSnapshot %s already exists in namespace %s.",
                snapshot_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to create VolumeSnapshot %s: %s %s",
                snapshot_name,
                exc.status,
                exc.reason,
            )
            raise

    return snapshot_name


def delete_volume_snapshot(namespace: str, snapshot_name: str) -> None:
    """Delete a VolumeSnapshot.

    Args:
        namespace: Namespace of the snapshot.
        snapshot_name: Name of the snapshot.

    Raises:
        ApiException: On unexpected Kubernetes API errors (404 is logged and ignored).
    """
    k8s = K8sClient.get_instance()

    try:
        k8s.custom_objects.delete_namespaced_custom_object(
            group=_SNAPSHOT_GROUP,
            version=_SNAPSHOT_VERSION,
            namespace=namespace,
            plural=_SNAPSHOT_PLURAL,
            name=snapshot_name,
        )
        logger.info(
            "Deleted VolumeSnapshot %s from namespace %s.", snapshot_name, namespace
        )
    except ApiException as exc:
        if exc.status == 404:
            logger.warning(
                "VolumeSnapshot %s not found in namespace %s; nothing to delete.",
                snapshot_name,
                namespace,
            )
        else:
            logger.error(
                "Failed to delete VolumeSnapshot %s: %s %s",
                snapshot_name,
                exc.status,
                exc.reason,
            )
            raise
