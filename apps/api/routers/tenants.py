from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from apps.api.database import get_db
from apps.api.middleware.auth import get_current_user, require_role, UserContext
from apps.api.repositories.tenant import TenantRepository
from apps.api.schemas.base import (
    TenantCreate, 
    TenantResponse, 
    OrganizationCreate, 
    OrganizationResponse,
    QuotaResponse
)
from apps.api.middleware.audit import log_audit_action

router = APIRouter(prefix="/tenants", tags=["Tenants & Organizations"])

@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_role("super-admin"))
):
    """Enables global super-admins to provision a new consolidative organization."""
    repo = TenantRepository(db)
    org = await repo.create_organization(req.name, req.slug)
    
    await log_audit_action(
        db=db,
        tenant_id=ctx.active_tenant_id,
        user_id=ctx.user_id,
        action="organization.create",
        resource="organization",
        resource_id=str(org.id),
        metadata={"slug": req.slug}
    )
    return org

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    req: TenantCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_role("admin"))
):
    """Enables admins to provision an isolated tenant boundary under an organization."""
    repo = TenantRepository(db)
    
    # Verify organization exists
    org = await repo.get_organization(req.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent organization not found"
        )
        
    tenant = await repo.create_tenant(req.organization_id, req.name, req.slug)
    
    # Auto-assign requesting administrator as tenant-owner of the new tenant
    await repo.add_membership(tenant.id, UUID(ctx.user_id), "tenant-owner")
    
    await log_audit_action(
        db=db,
        tenant_id=str(tenant.id),
        user_id=ctx.user_id,
        action="tenant.create",
        resource="tenant",
        resource_id=str(tenant.id),
        metadata={"slug": req.slug}
    )
    return tenant

@router.get("/quota", response_model=QuotaResponse, status_code=status.HTTP_200_OK)
async def get_tenant_quota(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Retrieves standard resource limits and monthly AI usage stats for active tenant."""
    repo = TenantRepository(db)
    quota = await repo.get_tenant_quota(UUID(ctx.active_tenant_id))
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quota settings not found for current active tenant"
        )
    return quota
