import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.models import AuditLog

logger = logging.getLogger("digitalq-audit")

async def log_audit_action(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Saves structural mutation events into audit_logs table and logs to standard stdout streams."""
    try:
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata=metadata
        )
        db.add(audit)
        await db.flush() # Flush to db transaction block
        
        logger.info(
            f"[AUDIT] Tenant: {tenant_id} | User: {user_id} | Action: {action} | Resource: {resource}:{resource_id}"
        )
    except Exception as e:
        logger.error(f"Failed to record audit event logs: {str(e)}")
        # Do not raise exception to avoid blocking the primary user request pipeline
