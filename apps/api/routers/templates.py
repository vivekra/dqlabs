from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from apps.api.database import get_db
from apps.api.middleware.auth import get_current_user, require_role, UserContext
from apps.api.repositories.template import TemplateRepository
from apps.api.schemas.base import LabTemplateCreate, LabTemplateResponse
from apps.api.middleware.audit import log_audit_action

router = APIRouter(prefix="/templates", tags=["Lab Templates"])

@router.get("", response_model=List[LabTemplateResponse], status_code=status.HTTP_200_OK)
async def list_active_templates(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Lists all available active lab templates (Kubernetes, DevOps and troubleshooting playgrounds)."""
    repo = TemplateRepository(db)
    return await repo.get_all_active()

@router.post("", response_model=LabTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_template(
    req: LabTemplateCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_role("instructor"))
):
    """Enables instructors or system admins to publish new workspace sandbox configurations."""
    repo = TemplateRepository(db)
    template = await repo.create(req)
    
    await log_audit_action(
        db=db,
        tenant_id=ctx.active_tenant_id,
        user_id=ctx.user_id,
        action="template.create",
        resource="template",
        resource_id=str(template.id),
        metadata={"slug": req.slug}
    )
    return template
