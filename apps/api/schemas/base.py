from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

# ==============================================================================
# 1. Organization Schemas
# ==============================================================================
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# ==============================================================================
# 2. Tenant Schemas
# ==============================================================================
class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)

class TenantCreate(TenantBase):
    organization_id: UUID

class TenantResponse(TenantBase):
    id: UUID
    organization_id: UUID
    status: str
    paymenter_client_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TenantMembershipResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# ==============================================================================
# 3. Lab Template Schemas
# ==============================================================================
class LabTemplateBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    category: str = Field(..., min_length=2, max_length=100)
    manifest_spec: Dict[str, Any]
    ai_runbook: str

class LabTemplateCreate(LabTemplateBase):
    pass

class LabTemplateResponse(LabTemplateBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ==============================================================================
# 4. Workspace Schemas
# ==============================================================================
class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    template_id: UUID
    allocated_cpu: float = Field(1.0, ge=0.5, le=32.0)
    allocated_ram_mb: int = Field(2048, ge=512, le=131072)
    allocated_storage_gb: int = Field(10, ge=1, le=1024)

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None # running, suspending, suspended, terminated

class WorkspaceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    template_id: Optional[UUID] = None
    name: str
    status: str
    pod_name: Optional[str] = None
    namespace: Optional[str] = None
    allocated_cpu: float
    allocated_ram_mb: int
    allocated_storage_gb: int
    ingress_url: Optional[str] = None
    last_active_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# ==============================================================================
# 5. Quota Schemas
# ==============================================================================
class QuotaResponse(BaseModel):
    tenant_id: UUID
    max_cpus: float
    max_ram_mb: int
    max_storage_gb: int
    max_workspaces: int
    max_ai_tokens_monthly: int
    used_ai_tokens_monthly: int
    updated_at: datetime

    class Config:
        from_attributes = True
