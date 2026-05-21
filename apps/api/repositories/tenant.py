from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.api.models import Tenant, Organization, TenantMembership, TenantQuota

class TenantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_tenant_quota(self, tenant_id: UUID) -> Optional[TenantQuota]:
        stmt = select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_tenant(self, organization_id: UUID, name: str, slug: str) -> Tenant:
        tenant = Tenant(
            organization_id=organization_id,
            name=name,
            slug=slug,
            status="active"
        )
        self.db.add(tenant)
        await self.db.flush()
        
        # Initialize default resource limits
        quota = TenantQuota(
            tenant_id=tenant.id,
            max_cpus=4.00,
            max_ram_mb=8192,
            max_storage_gb=50,
            max_workspaces=3,
            max_ai_tokens_monthly=1000000
        )
        self.db.add(quota)
        await self.db.flush()
        
        return tenant

    async def get_organization(self, organization_id: UUID) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_organization(self, name: str, slug: str) -> Organization:
        org = Organization(name=name, slug=slug)
        self.db.add(org)
        await self.db.flush()
        return org

    async def add_membership(self, tenant_id: UUID, user_id: UUID, role: str) -> TenantMembership:
        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role
        )
        self.db.add(membership)
        await self.db.flush()
        return membership
