import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, 
    String, 
    Boolean, 
    DateTime, 
    Numeric, 
    Integer, 
    ForeignKey, 
    JSON, 
    Enum,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from apps.api.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    memberships = relationship("TenantMembership", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tenants = relationship("Tenant", back_populates="organization", cascade="all, delete-orphan")

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    paymenter_client_id = Column(String(100), nullable=True)
    status = Column(String(50), default="active", index=True) # active, suspended, terminated
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="tenants")
    memberships = relationship("TenantMembership", back_populates="tenant", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="tenant", cascade="all, delete-orphan")
    quota = relationship("TenantQuota", uselist=False, back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("BillingSubscription", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="tenant-member", nullable=False) # super-admin, admin, instructor, student, tenant-owner, tenant-member
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

class TenantQuota(Base):
    __tablename__ = "tenant_quotas"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    max_cpus = Column(Numeric(5, 2), default=4.00, nullable=False)
    max_ram_mb = Column(Integer, default=8192, nullable=False)
    max_storage_gb = Column(Integer, default=50, nullable=False)
    max_workspaces = Column(Integer, default=3, nullable=False)
    max_ai_tokens_monthly = Column(Integer, default=1000000, nullable=False)
    used_ai_tokens_monthly = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="quota")

class LabTemplate(Base):
    __tablename__ = "lab_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    difficulty = Column(String(50), default="beginner") # beginner, intermediate, advanced
    category = Column(String(100), nullable=False) # kubernetes, devops, troubleshooting
    manifest_spec = Column(JSON, nullable=False) # Spec for deployment pod templates
    ai_runbook = Column(String, nullable=False) # Injected context
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="template")

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("lab_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="provisioning", index=True) # provisioning, running, idle, suspending, suspended, failed, terminated
    pod_name = Column(String(255), nullable=True)
    namespace = Column(String(255), nullable=True)
    allocated_cpu = Column(Numeric(5, 2), default=1.00)
    allocated_ram_mb = Column(Integer, default=2048)
    allocated_storage_gb = Column(Integer, default=10)
    ingress_url = Column(String(512), nullable=True)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="workspaces")
    user = relationship("User", back_populates="workspaces")
    template = relationship("LabTemplate", back_populates="workspaces")

class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    paymenter_subscription_id = Column(String(100), unique=True, nullable=False, index=True)
    plan_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, index=True) # active, unpaid, cancelled, suspended
    billing_type = Column(String(50), nullable=False) # fixed, resource-based
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="subscriptions")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True) # workspace.create, workspace.suspend, user.login
    resource = Column(String(100), nullable=False) # workspace, tenant, billing
    resource_id = Column(String(255), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
