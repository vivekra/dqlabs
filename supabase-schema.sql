-- Supabase Schema for DigitalQ Labs

-- Create tenants table
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create users table linked to Supabase auth
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    full_name TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create workspaces table
CREATE TABLE public.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create lab_templates table
CREATE TABLE public.lab_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    container_image TEXT NOT NULL,
    default_ports JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on workspaces
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view workspaces in their tenant
CREATE POLICY "Users can view workspaces in their tenant"
    ON public.workspaces
    FOR SELECT
    USING (tenant_id = (SELECT tenant_id FROM public.users WHERE id = auth.uid()));

-- Policy: Users can insert workspaces in their tenant
CREATE POLICY "Users can insert workspaces in their tenant"
    ON public.workspaces
    FOR INSERT
    WITH CHECK (tenant_id = (SELECT tenant_id FROM public.users WHERE id = auth.uid()));

-- Policy: Users can update workspaces they own or if they are in the same tenant (adjust as needed)
CREATE POLICY "Users can update workspaces in their tenant"
    ON public.workspaces
    FOR UPDATE
    USING (tenant_id = (SELECT tenant_id FROM public.users WHERE id = auth.uid()));

-- Policy: Users can delete workspaces they own
CREATE POLICY "Users can delete workspaces they own"
    ON public.workspaces
    FOR DELETE
    USING (owner_id = auth.uid());
