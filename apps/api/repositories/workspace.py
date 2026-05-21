from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from apps.api.models import Workspace, TenantQuota
from apps.api.schemas.base import WorkspaceCreate

class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Fetch active workspaces for tenant RLS filtering
    async def get_by_tenant(self, tenant_id: UUID) -> List[Workspace]:
        stmt = select(Workspace).where(Workspace.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # Get specific workspace checking tenant boundary
    async def get_by_id(self, tenant_id: UUID, workspace_id: UUID) -> Optional[Workspace]:
        stmt = select(Workspace).where(
            and_(Workspace.tenant_id == tenant_id, Workspace.id == workspace_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # Enforce quota limits before provisioning workspace
    async def verify_quota_allowance(
        self, 
        tenant_id: UUID, 
        req_cpu: float, 
        req_ram: int, 
        req_storage: int
    ) -> bool:
        # 1. Fetch current limits
        quota_stmt = select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        quota_res = await self.db.execute(quota_stmt)
        quota = quota_res.scalars().first()
        if not quota:
            return False # Default restrict if quota setup is missing
            
        # 2. Count current usage
        usage_stmt = select(
            func.count(Workspace.id).label("count"),
            func.sum(Workspace.allocated_cpu).label("cpu"),
            func.sum(Workspace.allocated_ram_mb).label("ram"),
            func.sum(Workspace.allocated_storage_gb).label("storage")
        ).where(
            Workspace.tenant_id == tenant_id,
            Workspace.status != "terminated"
        )
        usage_res = await self.db.execute(usage_stmt)
        usage = usage_res.first()
        
        current_count = usage[0] or 0
        current_cpu = float(usage[1] or 0.0)
        current_ram = usage[2] or 0
        current_storage = usage[3] or 0

        # Validate limits
        if current_count + 1 > quota.max_workspaces:
            return False
        if current_cpu + req_cpu > float(quota.max_cpus):
            return False
        if current_ram + req_ram > quota.max_ram_mb:
            return False
        if current_storage + req_storage > quota.max_storage_gb:
            return False

        return True

    # Register workspace instantiation
    async def create(self, tenant_id: UUID, user_id: UUID, schema: WorkspaceCreate) -> Workspace:
        workspace = Workspace(
            tenant_id=tenant_id,
            user_id=user_id,
            template_id=schema.template_id,
            name=schema.name,
            status="provisioning",
            allocated_cpu=schema.allocated_cpu,
            allocated_ram_mb=schema.allocated_ram_mb,
            allocated_storage_gb=schema.allocated_storage_gb,
            namespace=f"tenant-{str(tenant_id)[:8]}"
        )
        self.db.add(workspace)
        await self.db.flush()
        return workspace

    # Update state indicators
    async def update_status(self, workspace: Workspace, status: str) -> Workspace:
        workspace.status = status
        await self.db.flush()
        return workspace
