"""
Kubernetes client singleton for DigitalQ Labs orchestrator.

Provides a thread-safe singleton that auto-detects kubeconfig
(in-cluster first, then local fallback) and exposes typed API instances.
"""

import logging
import threading
from typing import Optional

from kubernetes import client, config
from kubernetes.client import (
    AppsV1Api,
    CoreV1Api,
    CustomObjectsApi,
    NetworkingV1Api,
)
from kubernetes.client.exceptions import ApiException

logger = logging.getLogger("digitalq.k8s.client")


class K8sClient:
    """Thread-safe Kubernetes client singleton.

    Auto-detects cluster configuration:
    1. In-cluster config (when running inside a pod)
    2. Local kubeconfig fallback (for development)

    Usage::

        k8s = K8sClient.get_instance()
        pods = k8s.core_v1.list_namespaced_pod("default")
    """

    _instance: Optional["K8sClient"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        raise RuntimeError(
            "Use K8sClient.get_instance() instead of direct instantiation."
        )

    @classmethod
    def get_instance(cls) -> "K8sClient":
        """Return the singleton K8sClient instance, creating it if needed.

        Returns:
            The shared K8sClient instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = object.__new__(cls)
                    instance._initialise()
                    cls._instance = instance
        return cls._instance

    def _initialise(self) -> None:
        """Load kubeconfig and create API instances."""
        self._load_config()
        api_client = client.ApiClient()
        self.core_v1: CoreV1Api = CoreV1Api(api_client)
        self.apps_v1: AppsV1Api = AppsV1Api(api_client)
        self.custom_objects: CustomObjectsApi = CustomObjectsApi(api_client)
        self.networking_v1: NetworkingV1Api = NetworkingV1Api(api_client)
        logger.info("Kubernetes API client initialised successfully.")

    @staticmethod
    def _load_config() -> None:
        """Attempt in-cluster config, falling back to local kubeconfig."""
        from apps.orchestrator.config import settings
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration.")
        except config.ConfigException:
            logger.info(
                "In-cluster config unavailable; falling back to local kubeconfig."
            )
            try:
                kubeconfig = settings.KUBECONFIG_PATH if settings.KUBECONFIG_PATH else None
                config.load_kube_config(config_file=kubeconfig)
                logger.info("Loaded local kubeconfig from %s.", kubeconfig or "default paths")

                # If running inside Docker and targetting host k3d, map localhost -> host.docker.internal
                if settings.ENVIRONMENT == "development":
                    c = client.Configuration.get_default_copy()
                    if "127.0.0.1" in c.host or "localhost" in c.host:
                        old_host = c.host
                        c.host = c.host.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")
                        client.Configuration.set_default(c)
                        logger.info("Auto-mapped local cluster endpoint from %s to %s for container network access.", old_host, c.host)
            except config.ConfigException as exc:
                logger.error("Failed to load any Kubernetes configuration: %s", exc)
                raise

    def health_check(self) -> bool:
        """Verify connectivity to the Kubernetes API server.

        Returns:
            True if the API server is reachable and healthy, False otherwise.
        """
        try:
            self.core_v1.get_api_resources()
            logger.debug("Kubernetes API health check passed.")
            return True
        except ApiException as exc:
            logger.warning(
                "Kubernetes API health check failed: %s %s",
                exc.status,
                exc.reason,
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Kubernetes API health check encountered unexpected error: %s", exc
            )
            return False

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        with cls._lock:
            cls._instance = None
            logger.info("K8sClient singleton has been reset.")
