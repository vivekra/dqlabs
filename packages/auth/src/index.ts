import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { UserRole, USER_ROLES } from '@digitalq/shared';

let supabaseInstance: SupabaseClient | null = null;

export function getSupabaseClient(url: string, anonKey: string): SupabaseClient {
  if (!supabaseInstance) {
    supabaseInstance = createClient(url, anonKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    });
  }
  return supabaseInstance;
}

// RBAC Authorization check helper
export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  const roleHierarchies: Record<UserRole, number> = {
    [USER_ROLES.SUPER_ADMIN]: 5,
    [USER_ROLES.ADMIN]: 4,
    [USER_ROLES.INSTRUCTOR]: 3,
    [USER_ROLES.TENANT_OWNER]: 2,
    [USER_ROLES.TENANT_MEMBER]: 1,
    [USER_ROLES.STUDENT]: 0,
  };

  return roleHierarchies[userRole] >= roleHierarchies[requiredRole];
}

// Validate Tenant switching authority
export function canSwitchToTenant(
  userId: string,
  targetTenantId: string,
  memberships: Array<{ tenantId: string; role: UserRole }>
): boolean {
  return memberships.some((m) => m.tenantId === targetTenantId);
}
