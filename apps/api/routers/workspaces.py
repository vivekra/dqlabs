from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
from celery import Celery

from apps.api.database import get_db
from apps.api.middleware.auth import get_current_user, UserContext
from apps.api.repositories.workspace import WorkspaceRepository
from apps.api.repositories.template import TemplateRepository
from apps.api.schemas.base import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from apps.api.middleware.audit import log_audit_action
from apps.api.config import settings

router = APIRouter(prefix="/workspaces", tags=["Workspaces & Playgrounds"])

# Local Celery app instantiation to send tasks to apps/orchestrator
celery_app = Celery("digitalq_tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@router.get("", response_model=List[WorkspaceResponse], status_code=status.HTTP_200_OK)
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Lists active/suspended workspaces assigned to the active tenant domain."""
    repo = WorkspaceRepository(db)
    return await repo.get_by_tenant(UUID(ctx.active_tenant_id))

@router.get("/{workspace_id}", response_model=WorkspaceResponse, status_code=status.HTTP_200_OK)
async def get_workspace(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Fetch details of a specific workspace, strictly validating tenant boundary access."""
    repo = WorkspaceRepository(db)
    ws = await repo.get_by_id(UUID(ctx.active_tenant_id), workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access"
        )
    return ws

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    req: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Provisions a new lab workspace, performing strict resource quota allowance check."""
    ws_repo = WorkspaceRepository(db)
    tpl_repo = TemplateRepository(db)
    
    # 1. Verify template exists
    tpl = await tpl_repo.get_by_id(req.template_id)
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target lab template not found"
        )

    # 2. Check quota allowances
    has_quota = await ws_repo.verify_quota_allowance(
        tenant_id=UUID(ctx.active_tenant_id),
        req_cpu=req.allocated_cpu,
        req_ram=req.allocated_ram_mb,
        req_storage=req.allocated_storage_gb
    )
    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant resource quotas exceeded. Suspend or terminate existing workspaces."
        )

    # 3. Create database state row
    ws = await ws_repo.create(UUID(ctx.active_tenant_id), UUID(ctx.user_id), req)
    
    # 4. Trigger Celery worker in background to schedule workspace pods on runtime cluster
    try:
        celery_app.send_task(
            "tasks.provision_workspace",
            args=[str(ws.id), str(ctx.active_tenant_id)]
        )
    except Exception as e:
        # Update status to failed if broker dispatch fails
        await ws_repo.update_status(ws, "failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch provision task to orchestrator: {str(e)}"
        )

    # Record action in audit logs
    await log_audit_action(
        db=db,
        tenant_id=ctx.active_tenant_id,
        user_id=ctx.user_id,
        action="workspace.create",
        resource="workspace",
        resource_id=str(ws.id),
        metadata={"name": req.name, "template_id": str(req.template_id)}
    )
    return ws

@router.put("/{workspace_id}", response_model=WorkspaceResponse, status_code=status.HTTP_200_OK)
async def update_workspace_status(
    workspace_id: UUID,
    req: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """Enables students/admins to trigger workspace state machine changes (suspend / resume / terminate)."""
    ws_repo = WorkspaceRepository(db)
    ws = await ws_repo.get_by_id(UUID(ctx.active_tenant_id), workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access"
        )

    if req.status:
        target_status = req.status.lower()
        
        if target_status == "suspending":
            if ws.status != "running":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot suspend a workspace in '{ws.status}' state."
                )
            await ws_repo.update_status(ws, "suspending")
            celery_app.send_task("tasks.suspend_workspace", args=[str(ws.id)])
            
            await log_audit_action(
                db=db,
                tenant_id=ctx.active_tenant_id,
                user_id=ctx.user_id,
                action="workspace.suspend",
                resource="workspace",
                resource_id=str(ws.id)
            )

        elif target_status == "running": # Resuming a suspended workspace
            if ws.status != "suspended":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot resume a workspace in '{ws.status}' state."
                )
            await ws_repo.update_status(ws, "provisioning")
            celery_app.send_task("tasks.provision_workspace", args=[str(ws.id), str(ctx.active_tenant_id)])
            
            await log_audit_action(
                db=db,
                tenant_id=ctx.active_tenant_id,
                user_id=ctx.user_id,
                action="workspace.resume",
                resource="workspace",
                resource_id=str(ws.id)
            )

        elif target_status == "terminated":
            await ws_repo.update_status(ws, "terminated")
            # Enforce clean-up in Celery queue
            celery_app.send_task("tasks.terminate_workspace", args=[str(ws.id)])
            
            await log_audit_action(
                db=db,
                tenant_id=ctx.active_tenant_id,
                user_id=ctx.user_id,
                action="workspace.terminate",
                resource="workspace",
                resource_id=str(ws.id)
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition state target: {req.status}"
            )

    if req.name:
        ws.name = req.name

    return ws
