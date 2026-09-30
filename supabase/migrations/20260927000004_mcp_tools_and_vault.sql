-- Migration: 20260927000004_mcp_tools_and_vault.sql
-- Description: Dynamic MCP tool discovery cache, tool execution audit trail, and Supabase Vault linkage (Spec 04)

-- 1. Discovered Tools Cache Table
CREATE TABLE IF NOT EXISTS public.discovered_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES public.mcp_connections(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    parameters_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_critical BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for fast tool lookup during turn initialization
CREATE INDEX IF NOT EXISTS idx_discovered_tools_user_org ON public.discovered_tools(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_discovered_tools_provider ON public.discovered_tools(provider);

-- 2. Tool Invocations Audit Log Table
CREATE TABLE IF NOT EXISTS public.tool_invocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    session_id TEXT,
    tool_name TEXT NOT NULL,
    provider TEXT,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'executed' CHECK (status IN ('pending_approval', 'approved', 'declined', 'executed', 'failed')),
    output JSONB,
    error_message TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for compliance audit querying
CREATE INDEX IF NOT EXISTS idx_tool_invocations_user_org ON public.tool_invocations(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool_name ON public.tool_invocations(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_created_at ON public.tool_invocations(created_at DESC);

-- 3. Enable Row-Level Security (RLS)
ALTER TABLE public.discovered_tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tool_invocations ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies: Discovered Tools
CREATE POLICY "Users can view own discovered tools"
    ON public.discovered_tools
    FOR SELECT
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can insert own discovered tools"
    ON public.discovered_tools
    FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can update own discovered tools"
    ON public.discovered_tools
    FOR UPDATE
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    )
    WITH CHECK (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can delete own discovered tools"
    ON public.discovered_tools
    FOR DELETE
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

-- 5. RLS Policies: Tool Invocations Audit Log
CREATE POLICY "Users can view own tool invocations"
    ON public.tool_invocations
    FOR SELECT
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can insert own tool invocations"
    ON public.tool_invocations
    FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can update own tool invocations status"
    ON public.tool_invocations
    FOR UPDATE
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    )
    WITH CHECK (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );
