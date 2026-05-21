const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const AI_URL = process.env.NEXT_PUBLIC_AI_GATEWAY_URL || 'http://localhost:8001';

interface RequestOptions {
  token: string;
  tenantId: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: Record<string, unknown>;
}

async function apiFetch<T>(path: string, opts: RequestOptions): Promise<T> {
  const res = await fetch(`${BASE_URL}/api/v1${path}`, {
    method: opts.method ?? 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${opts.token}`,
      'X-Tenant-ID': opts.tenantId,
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail: string }).detail || `API error ${res.status}`);
  }

  return res.json() as Promise<T>;
}

import type { Workspace, LabTemplate } from '../store/workspaceStore';

export const api = {
  // Workspaces
  listWorkspaces: (token: string, tenantId: string) =>
    apiFetch<Workspace[]>('/workspaces', { token, tenantId }),

  createWorkspace: (
    token: string,
    tenantId: string,
    body: {
      template_id: string;
      name: string;
      allocated_cpu: number;
      allocated_ram_mb: number;
      allocated_storage_gb: number;
    }
  ) => apiFetch<Workspace>('/workspaces', { token, tenantId, method: 'POST', body }),

  updateWorkspace: (
    token: string,
    tenantId: string,
    id: string,
    body: { status?: string; name?: string }
  ) => apiFetch<Workspace>(`/workspaces/${id}`, { token, tenantId, method: 'PUT', body }),

  getWorkspace: (token: string, tenantId: string, id: string) =>
    apiFetch<Workspace>(`/workspaces/${id}`, { token, tenantId }),

  // Templates
  listTemplates: (token: string, tenantId: string) =>
    apiFetch<LabTemplate[]>('/templates', { token, tenantId }),

  // AI Gateway
  diagnose: async (query: string, errorLogs?: string) => {
    const res = await fetch(`${AI_URL}/api/v1/ai/diagnose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, error_logs: errorLogs }),
    });
    if (!res.ok) throw new Error('AI gateway error');
    return res.json() as Promise<{
      source: string;
      model: string;
      diagnosis: string;
      correction_command: string;
    }>;
  },
};

// ─── Mock data for local development without a live cluster ─────────────────

export const MOCK_WORKSPACES: Workspace[] = [
  {
    id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    name: 'K8s Production Playground',
    status: 'running',
    ingress_url: 'https://ws-a1b2c3d4.dq-tenant1.digitalqlabs.io',
    namespace: 'dq-tenant1',
    pod_name: 'ws-a1b2c3d4',
    allocated_cpu: 2,
    allocated_ram_mb: 4096,
    allocated_storage_gb: 20,
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    template_id: 'tpl-001',
  },
  {
    id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    name: 'DevOps CI/CD Lab',
    status: 'suspended',
    ingress_url: null,
    namespace: 'dq-tenant1',
    pod_name: null,
    allocated_cpu: 1,
    allocated_ram_mb: 2048,
    allocated_storage_gb: 10,
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    template_id: 'tpl-002',
  },
  {
    id: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
    name: 'Networking Troubleshooting',
    status: 'provisioning',
    ingress_url: null,
    namespace: 'dq-tenant1',
    pod_name: null,
    allocated_cpu: 2,
    allocated_ram_mb: 4096,
    allocated_storage_gb: 15,
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 60 * 1000).toISOString(),
    template_id: 'tpl-003',
  },
];

export const MOCK_TEMPLATES: LabTemplate[] = [
  {
    id: 'tpl-001',
    title: 'Kubernetes Fundamentals',
    slug: 'k8s-fundamentals',
    description: 'Master pod scheduling, deployments, services and config management on a live cluster.',
    difficulty: 'beginner',
    category: 'kubernetes',
    is_active: true,
  },
  {
    id: 'tpl-002',
    title: 'GitOps & ArgoCD',
    slug: 'gitops-argocd',
    description: 'Set up GitOps pipelines using ArgoCD with automatic sync and rollback strategies.',
    difficulty: 'intermediate',
    category: 'devops',
    is_active: true,
  },
  {
    id: 'tpl-003',
    title: 'Service Mesh with Istio',
    slug: 'service-mesh-istio',
    description: 'Configure Istio sidecar injection, traffic management, and mTLS in your namespace.',
    difficulty: 'advanced',
    category: 'networking',
    is_active: true,
  },
  {
    id: 'tpl-004',
    title: 'CrashLoop Debugging',
    slug: 'crashloop-debug',
    description: 'Troubleshoot failing pods using kubectl events, logs, and resource diagnostics.',
    difficulty: 'intermediate',
    category: 'troubleshooting',
    is_active: true,
  },
];

// Build a terminal WebSocket URL for a running workspace
export function buildTerminalWsUrl(workspace: Workspace, token: string): string {
  if (!workspace.ingress_url) return '';
  const wsUrl = workspace.ingress_url.replace(/^https?:\/\//, 'wss://');
  return `${wsUrl}/terminal/ws?token=${encodeURIComponent(token)}&tenant_id=${encodeURIComponent(workspace.namespace || '')}`;
}
