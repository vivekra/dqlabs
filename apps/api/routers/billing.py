import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel, Field

from apps.api.database import get_db
from apps.api.middleware.auth import get_current_user, UserContext
from apps.api.repositories.tenant import TenantRepository
from apps.api.models import TenantQuota
from apps.api.middleware.audit import log_audit_action

logger = logging.getLogger("digitalq-billing")
router = APIRouter(prefix="/billing", tags=["Billing & Metering"])

class MeterUsageRequest(BaseModel):
    tokens_consumed: int = Field(..., ge=0)
    cpu_hours: float = Field(..., ge=0.0)
    ram_mb_hours: int = Field(..., ge=0)

@router.post("/meter", status_code=status.HTTP_200_OK)
async def record_usage(
    req: MeterUsageRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Enables runtime agents or gateways to meter resource usage limits (tokens, cpu, ram)."""
    repo = TenantRepository(db)
    
    # 1. Retrieve current quota
    quota = await repo.get_tenant_quota(UUID(ctx.active_tenant_id))
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quota settings not found for current tenant context"
        )

    # 2. Add consumed AI tokens to monthly metric tracker
    quota.used_ai_tokens_monthly += req.tokens_consumed
    await db.flush()

    logger.info(
        f"[METERING] Tenant: {ctx.active_tenant_id} | Added {req.tokens_consumed} AI tokens, "
        f"{req.cpu_hours} CPU-hours, {req.ram_mb_hours} MB-RAM-hours."
    )

    await log_audit_action(
        db=db,
        tenant_id=ctx.active_tenant_id,
        user_id=ctx.user_id,
        action="billing.usage_metered",
        resource="billing",
        resource_id=ctx.active_tenant_id,
        metadata={
            "tokens": req.tokens_consumed,
            "cpu_hours": req.cpu_hours,
            "ram_mb_hours": req.ram_mb_hours
        }
    )
    return {
        "status": "success",
        "total_used_tokens_monthly": quota.used_ai_tokens_monthly,
        "max_ai_tokens_monthly": quota.max_ai_tokens_monthly
    }
