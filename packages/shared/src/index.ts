import { z } from 'zod';

// Shared User Roles Constants
export const USER_ROLES = {
  SUPER_ADMIN: 'super-admin',
  ADMIN: 'admin',
  INSTRUCTOR: 'instructor',
  STUDENT: 'student',
  TENANT_OWNER: 'tenant-owner',
  TENANT_MEMBER: 'tenant-member',
} as const;

export type UserRole = typeof USER_ROLES[keyof typeof USER_ROLES];

// Shared Workspace Status Constants
export const WORKSPACE_STATUSES = {
  PROVISIONING: 'provisioning',
  RUNNING: 'running',
  SUSPENDING: 'suspending',
  SUSPENDED: 'suspended',
  FAILED: 'failed',
  TERMINATED: 'terminated',
} as const;

export type WorkspaceStatus = typeof WORKSPACE_STATUSES[keyof typeof WORKSPACE_STATUSES];

// Shared Schema Definitions using Zod
export const WorkspaceConfigSchema = z.object({
  template_id: z.string().uuid(),
  name: z.string().min(1).max(255),
  cpu: z.number().positive().max(32),
  ram_mb: z.number().int().positive().max(131072),
  storage_gb: z.number().int().positive().max(1024),
});

export type WorkspaceConfig = z.infer<typeof WorkspaceConfigSchema>;

export const TenantQuotaSchema = z.object({
  max_cpus: z.number().positive(),
  max_ram_mb: z.number().int().positive(),
  max_storage_gb: z.number().int().positive(),
  max_workspaces: z.number().int().positive(),
  max_ai_tokens_monthly: z.number().int().positive(),
});

export type TenantQuota = z.infer<typeof TenantQuotaSchema>;
