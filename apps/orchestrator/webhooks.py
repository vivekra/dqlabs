import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends
from .auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks/paymenter", tags=["webhooks", "paymenter"])

@router.post("/service-created")
async def service_created(payload: Dict[Any, Any], token: dict = Depends(verify_token)):
    user_email = payload.get("user", {}).get("email")
    if not user_email:
        user_email = payload.get("email", "unknown@example.com")
        
    logger.info(f"Paymenter webhook received: Create workspace for user {user_email}")
    
    # Skeleton logic: dispatch Celery task to create workspace
    # create_workspace.delay(user_email, payload)
    
    return {"status": "ok", "message": f"Workspace creation initiated for {user_email}"}

@router.post("/service-suspended")
async def service_suspended(payload: Dict[Any, Any], token: dict = Depends(verify_token)):
    user_email = payload.get("user", {}).get("email")
    if not user_email:
        user_email = payload.get("email", "unknown@example.com")
        
    logger.info(f"Paymenter webhook received: Suspend workspace for user {user_email}")
    
    # Skeleton logic: dispatch Celery task to suspend workspace
    # suspend_workspace.delay(user_email, payload)
    
    return {"status": "ok", "message": f"Workspace suspension initiated for {user_email}"}
