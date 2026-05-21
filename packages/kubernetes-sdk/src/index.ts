import * as k8s from '@kubernetes/client-node';

export class KubernetesClusterManager {
  private kc: k8s.KubeConfig;
  private k8sApi: k8s.CoreV1Api;
  private appsApi: k8s.AppsV1Api;
  private networkingApi: k8s.NetworkingV1Api;

  constructor() {
    this.kc = new k8s.KubeConfig();
    try {
      this.kc.loadFromDefault();
    } catch {
      // Fallback: loading cluster configuration in-pod for local production deployments
      this.kc.loadFromCluster();
    }
    this.k8sApi = this.kc.makeApiClient(k8s.CoreV1Api);
    this.appsApi = this.kc.makeApiClient(k8s.AppsV1Api);
    this.networkingApi = this.kc.makeApiClient(k8s.NetworkingV1Api);
  }

  // Provision namespace isolated by resource boundaries
  async provisionNamespace(namespaceName: string, cpuLimit: string, memoryLimit: string): Promise<void> {
    const ns = {
      apiVersion: 'v1',
      kind: 'Namespace',
      metadata: { name: namespaceName },
    };

    const quota = {
      apiVersion: 'v1',
      kind: 'ResourceQuota',
      metadata: { name: 'tenant-quota', namespace: namespaceName },
      spec: {
        hard: {
          'limits.cpu': cpuLimit,
          'limits.memory': memoryLimit,
          'persistentvolumeclaims': '5',
        },
      },
    };

    try {
      await this.k8sApi.createNamespace(ns);
      await this.k8sApi.createNamespacedResourceQuota(namespaceName, quota);
    } catch (error) {
      console.error(`Kubernetes namespace provisioning error for: ${namespaceName}`, error);
      throw new Error('K8s resource setup failure');
    }
  }

  // Teardown workspace/namespace resources on deletion
  async teardownNamespace(namespaceName: string): Promise<void> {
    try {
      await this.k8sApi.deleteNamespace(namespaceName);
    } catch (error) {
      console.error(`Kubernetes namespace teardown failed for: ${namespaceName}`, error);
      throw new Error('K8s resource teardown failure');
    }
  }

  // Define dynamic Traefik Ingress routing for code-server & terminal websockets
  async createIngressRoute(
    namespace: string,
    workspaceId: string,
    hostDomain: string,
    serviceName: string,
    port: number
  ): Promise<string> {
    const ingressName = `ingress-ws-${workspaceId}`;
    const ingressSpec: k8s.V1Ingress = {
      apiVersion: 'networking.k8s.io/v1',
      kind: 'Ingress',
      metadata: {
        name: ingressName,
        namespace,
        annotations: {
          'traefik.ingress.kubernetes.io/router.entrypoints': 'websecure',
          'traefik.ingress.kubernetes.io/router.tls': 'true',
        },
      },
      spec: {
        rules: [
          {
            host: hostDomain,
            http: {
              paths: [
                {
                  path: '/',
                  pathType: 'Prefix',
                  backend: {
                    service: {
                      name: serviceName,
                      port: { number: port },
                    },
                  },
                },
              ],
            },
          },
        ],
      },
    };

    try {
      await this.networkingApi.createNamespacedIngress(namespace, ingressSpec);
      return `https://${hostDomain}`;
    } catch (error) {
      console.error(`Kubernetes ingress route mapping failed for workspace: ${workspaceId}`, error);
      throw new Error('K8s ingress routing configuration error');
    }
  }
}
