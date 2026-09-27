-- Migration: 20260927000001_auth_and_users.sql
-- Description: Core tables for Identity, Organizations, Profiles, DPDP Consent, MCP Connections & RLS

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pgsodium and vault if available
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS "pgsodium";
    CREATE EXTENSION IF NOT EXISTS "supabase_vault";
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Vault extension initialization skipped in local fallback';
END $$;

-- 2. Organizations Table
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domains TEXT[] NOT NULL DEFAULT '{}',
    is_demo BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'tool-admin', 'org-admin')),
    first_name TEXT,
    last_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. User Consents Table (DPDP Act 2023 Statutory Consent)
CREATE TABLE IF NOT EXISTS public.user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    consent_version TEXT NOT NULL DEFAULT '2026.1',
    language TEXT NOT NULL DEFAULT 'en' CHECK (language IN ('en', 'hi')),
    ip_address TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    consented_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. MCP Connections Table
CREATE TABLE IF NOT EXISTS public.mcp_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    vault_secret_id UUID,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for high performance
CREATE INDEX IF NOT EXISTS idx_organizations_domains ON public.organizations USING GIN (domains);
CREATE INDEX IF NOT EXISTS idx_profiles_org_id ON public.profiles(org_id);
CREATE INDEX IF NOT EXISTS idx_user_consents_user_org ON public.user_consents(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_mcp_connections_user_org ON public.mcp_connections(user_id, org_id);

-- 6. Enable Row-Level Security (RLS)
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mcp_connections ENABLE ROW LEVEL SECURITY;

-- 7. RLS Policies

-- Organizations: users can only view their own organization
CREATE POLICY "Users can view their organization"
    ON public.organizations
    FOR SELECT
    USING (
        id = NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid
        OR id IN (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

-- Profiles: users can view all profiles in their organization, edit only their own
CREATE POLICY "Users can view profiles in their organization"
    ON public.profiles
    FOR SELECT
    USING (
        org_id = NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid
        OR org_id IN (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can update their own profile"
    ON public.profiles
    FOR UPDATE
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- User Consents: users can read and insert their own consent
CREATE POLICY "Users can read own consent records"
    ON public.user_consents
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can record own consent"
    ON public.user_consents
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- MCP Connections: strictly isolated per user and tenant
CREATE POLICY "Users can view own mcp connections"
    ON public.mcp_connections
    FOR SELECT
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can insert own mcp connections"
    ON public.mcp_connections
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can update own mcp connections"
    ON public.mcp_connections
    FOR UPDATE
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can delete own mcp connections"
    ON public.mcp_connections
    FOR DELETE
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

-- 8. Domain Whitelist Verification & Auto-Provisioning Hook
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    user_domain TEXT;
    matched_org_id UUID;
BEGIN
    -- Extract domain from email
    user_domain := split_part(NEW.email, '@', 2);
    
    -- Check if domain is authorized in public.organizations
    SELECT id INTO matched_org_id
    FROM public.organizations
    WHERE user_domain = ANY(domains)
    LIMIT 1;
    
    IF matched_org_id IS NULL THEN
        RAISE EXCEPTION 'Domain not authorized for this workspace: %', user_domain
            USING ERRCODE = 'P0001';
    END IF;
    
    -- Insert profile
    INSERT INTO public.profiles (id, org_id, email, role, first_name, last_name, avatar_url)
    VALUES (
        NEW.id,
        matched_org_id,
        NEW.email,
        'member',
        COALESCE(NEW.raw_user_meta_data->>'first_name', split_part(NEW.email, '@', 1)),
        NEW.raw_user_meta_data->>'last_name',
        NEW.raw_user_meta_data->>'avatar_url'
    )
    ON CONFLICT (id) DO UPDATE SET
        org_id = EXCLUDED.org_id,
        email = EXCLUDED.email;
        
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users after insert
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
