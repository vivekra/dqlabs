import jwt
from typing import Optional
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.api.config import settings
from apps.api.database import get_db
from apps.api.models import User, TenantMembership, Tenant

security = HTTPBearer()

# Role weights to evaluate RBAC hierarchy
ROLE_WEIGHTS = {
    "super-admin": 5,
    "admin": 4,
    "instructor": 3,
    "tenant-owner": 2,
    "tenant-member": 1,
    "student": 0,
}

class UserContext:
    def __init__(self, user_id: str, email: str, active_tenant_id: str, role: str, is_superadmin: bool = False):
        self.user_id = user_id
        self.email = email
        self.active_tenant_id = active_tenant_id
        self.role = role
        self.is_superadmin = is_superadmin

async def get_current_user(
    req: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> UserContext:
    """Dependency that decodes Supabase JWT, validates tenant X-Tenant-ID context and membership."""
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials are required"
        )
        
    token = creds.credentials
    try:
        # Decode and validate token against Supabase local/cloud secret
        payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid JWT claims"
            )
            
        # Parse active tenant header from client
        active_tenant_id = req.headers.get("X-Tenant-ID")
        if not active_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID header is required"
            )

        # Check membership and role inside target tenant
        stmt = select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == active_tenant_id
        )
        result = await db.execute(stmt)
        membership = result.scalars().first()
        
        if not membership:
            # Check if global user is super-admin
            user_stmt = select(User).where(User.id == user_id)
            user_res = await db.execute(user_stmt)
            user_obj = user_res.scalars().first()
            
            if user_obj and user_obj.is_superadmin:
                return UserContext(
                    user_id=user_id,
                    email=email,
                    active_tenant_id=active_tenant_id,
                    role="super-admin",
                    is_superadmin=True
                )
                
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource requires active tenant membership"
            )

        return UserContext(
            user_id=user_id,
            email=email,
            active_tenant_id=active_tenant_id,
            role=membership.role
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization token")

def require_role(required_role: str):
    """Enforces RBAC boundaries based on role hierarchy weights."""
    async def role_dependency(ctx: UserContext = Depends(get_current_user)) -> UserContext:
        if ctx.is_superadmin:
            return ctx
            
        user_weight = ROLE_WEIGHTS.get(ctx.role, -1)
        required_weight = ROLE_WEIGHTS.get(required_role, 99)
        
        if user_weight < required_weight:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires role: {required_role} (Current: {ctx.role})"
            )
        return ctx
    return role_dependency

async def verify_websocket_token(
    token: str,
    active_tenant_id: str,
    db: AsyncSession
) -> UserContext:
    """Validates Supabase JWT and active tenant membership for WebSockets upgrades."""
    try:
        payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise ValueError("Invalid credentials inside WebSocket token")

        # Check membership and role inside target tenant
        stmt = select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == active_tenant_id
        )
        result = await db.execute(stmt)
        membership = result.scalars().first()
        
        if not membership:
            # Check superadmin status
            user_stmt = select(User).where(User.id == user_id)
            user_res = await db.execute(user_stmt)
            user_obj = user_res.scalars().first()
            
            if user_obj and user_obj.is_superadmin:
                return UserContext(
                    user_id=user_id,
                    email=email,
                    active_tenant_id=active_tenant_id,
                    role="super-admin",
                    is_superadmin=True
                )
            raise ValueError("User has no active membership in target tenant")

        return UserContext(
            user_id=user_id,
            email=email,
            active_tenant_id=active_tenant_id,
            role=membership.role
        )

    except jwt.PyJWTError as e:
        raise ValueError(f"WebSocket JWT invalidation error: {str(e)}")
