-- ==============================================================================
-- DigitalQ Labs - Local PostgreSQL DB Initialization & Seed Data Script
-- ==============================================================================

-- Enable vector extension for AI gateway searches
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Drop existing tables to ensure a clean run
DROP TABLE IF EXISTS workspaces CASCADE;
DROP TABLE IF EXISTS lab_templates CASCADE;
DROP TABLE IF EXISTS tenant_quotas CASCADE;
DROP TABLE IF EXISTS tenant_memberships CASCADE;
DROP TABLE IF EXISTS billing_subscriptions CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- 1. Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    paymenter_client_id VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Users Table (Mirroring local Supabase Auth structure)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    is_superadmin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. User-Tenant Memberships
CREATE TABLE tenant_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'tenant-member',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, user_id)
);

-- 5. Quotas
CREATE TABLE tenant_quotas (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    max_cpus NUMERIC(5,2) NOT NULL DEFAULT 4.00,
    max_ram_mb INTEGER NOT NULL DEFAULT 8192,
    max_storage_gb INTEGER NOT NULL DEFAULT 50,
    max_workspaces INTEGER NOT NULL DEFAULT 3,
    max_ai_tokens_monthly INTEGER NOT NULL DEFAULT 1000000,
    used_ai_tokens_monthly INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Lab Templates
CREATE TABLE lab_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    difficulty VARCHAR(50) DEFAULT 'beginner',
    category VARCHAR(100) NOT NULL,
    manifest_spec JSONB NOT NULL,
    ai_runbook TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Workspaces
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    template_id UUID REFERENCES lab_templates(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'provisioning',
    pod_name VARCHAR(255),
    namespace VARCHAR(255),
    allocated_cpu NUMERIC(5,2) DEFAULT 1.00,
    allocated_ram_mb INTEGER DEFAULT 2048,
    allocated_storage_gb INTEGER DEFAULT 10,
    ingress_url VARCHAR(512),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- Seed Mock Data
-- ==============================================================================

-- Seed Default Organization & Tenant
INSERT INTO organizations (id, name, slug) 
VALUES ('c13ce7b2-3c22-42db-a51c-4b62db47b198', 'DigitalQ Academy', 'digitalq-academy');

INSERT INTO tenants (id, organization_id, name, slug, status) 
VALUES ('22ffda8c-3c33-41bb-b50a-e3dbf3da92cb', 'c13ce7b2-3c22-42db-a51c-4b62db47b198', 'DevOps bootcamp', 'devops-bootcamp', 'active');

-- Seed Default Admin User
INSERT INTO users (id, email, full_name, is_superadmin) 
VALUES ('8c459f42-4f32-4d2a-89aa-9b6f3c1a329d', 'admin@digitalqlabs.io', 'Master Architect', TRUE);

-- User Tenant Association
INSERT INTO tenant_memberships (tenant_id, user_id, role) 
VALUES ('22ffda8c-3c33-41bb-b50a-e3dbf3da92cb', '8c459f42-4f32-4d2a-89aa-9b6f3c1a329d', 'super-admin');

-- Quota limits allocation
INSERT INTO tenant_quotas (tenant_id, max_cpus, max_ram_mb, max_storage_gb, max_workspaces, max_ai_tokens_monthly)
VALUES ('22ffda8c-3c33-41bb-b50a-e3dbf3da92cb', 8.00, 16384, 100, 5, 2500000);

-- Seed Lab Templates
INSERT INTO lab_templates (id, title, slug, description, difficulty, category, manifest_spec, ai_runbook)
VALUES (
    'b13ce7b2-3c22-42db-a51c-4b62db47b198',
    'K3s Troubleshooting Arena',
    'k3s-troubleshooting-arena',
    'Locate and fix a broken readinessProbe configuration inside a failing deployment namespace.',
    'intermediate',
    'troubleshooting',
    '{"image": "digitalqlabs/code-server:v1.0.0", "ports": [8080]}',
    'Grading Criteria: Student resolves the readinessProbe path by editing deployment.yaml in workspace and ensuring Pod matches status Running.'
);

INSERT INTO lab_templates (id, title, slug, description, difficulty, category, manifest_spec, ai_runbook)
VALUES (
    'a55ce7b2-3c22-42db-a51c-4b62db47b199',
    'EKS Anywhere Simulation Playground',
    'eks-anywhere-playground',
    'Build multi-node Kubernetes clusters simulating Amazon EKS Anywhere environment locally.',
    'advanced',
    'kubernetes',
    '{"image": "digitalqlabs/systemd-k3s-sim:v1.0.0", "ports": [8080, 3000]}',
    'Grading Criteria: Validate multi-node deployment via cluster configuration file mapping.'
);

-- Seed Initial Active Workspace
INSERT INTO workspaces (id, tenant_id, user_id, template_id, name, status, pod_name, namespace, allocated_cpu, allocated_ram_mb, allocated_storage_gb, ingress_url)
VALUES (
    '8c459f42-4f32-4d2a-89aa-9b6f3c1a329d',
    '22ffda8c-3c33-41bb-b50a-e3dbf3da92cb',
    '8c459f42-4f32-4d2a-89aa-9b6f3c1a329d',
    'b13ce7b2-3c22-42db-a51c-4b62db47b198',
    'Production K8s Playground',
    'running',
    'ws-pod-8c459f42',
    'tenant-devops-bootcamp',
    2.00,
    4096,
    20,
    'https://ws-8c459f42.22ffda8c.digitalqlabs.io'
);
