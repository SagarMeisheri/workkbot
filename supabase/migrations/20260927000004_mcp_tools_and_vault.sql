-- Migration: 20260927000004_mcp_tools_and_vault.sql
-- Description: Dynamic MCP tool connections, discovered tools cache, tool execution audit trail with Composio log_id, and Supabase Vault linkage (Spec 04)

-- 1. Tool Connections Table (Composio sessions, connected accounts, and Supabase Vault links)
CREATE TABLE IF NOT EXISTS public.tool_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    session_id TEXT,
    connected_account_id TEXT,
    vault_secret_id UUID,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disconnected', 'expired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tool_connections_user_org ON public.tool_connections(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_tool_connections_provider ON public.tool_connections(provider);
CREATE INDEX IF NOT EXISTS idx_tool_connections_session_id ON public.tool_connections(session_id);

-- 2. Discovered Tools Cache Table
CREATE TABLE IF NOT EXISTS public.discovered_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES public.tool_connections(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    tool_slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    parameters_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_critical BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_discovered_tools_user_org ON public.discovered_tools(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_discovered_tools_provider ON public.discovered_tools(provider);
CREATE INDEX IF NOT EXISTS idx_discovered_tools_slug ON public.discovered_tools(tool_slug);

-- 3. Tool Invocations Audit Log Table
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
    composio_log_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tool_invocations_user_org ON public.tool_invocations(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool_name ON public.tool_invocations(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_composio_log ON public.tool_invocations(composio_log_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_created_at ON public.tool_invocations(created_at DESC);

-- 4. Enable Row-Level Security (RLS)
ALTER TABLE public.tool_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discovered_tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tool_invocations ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies: Tool Connections
CREATE POLICY "Users can view own tool connections"
    ON public.tool_connections
    FOR SELECT
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can insert own tool connections"
    ON public.tool_connections
    FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can update own tool connections"
    ON public.tool_connections
    FOR UPDATE
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    )
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can delete own tool connections"
    ON public.tool_connections
    FOR DELETE
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 6. RLS Policies: Discovered Tools
CREATE POLICY "Users can view own discovered tools"
    ON public.discovered_tools
    FOR SELECT
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can insert own discovered tools"
    ON public.discovered_tools
    FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can update own discovered tools"
    ON public.discovered_tools
    FOR UPDATE
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    )
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can delete own discovered tools"
    ON public.discovered_tools
    FOR DELETE
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 7. RLS Policies: Tool Invocations Audit Log
CREATE POLICY "Users can view own tool invocations"
    ON public.tool_invocations
    FOR SELECT
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can insert own tool invocations"
    ON public.tool_invocations
    FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can update own tool invocations status"
    ON public.tool_invocations
    FOR UPDATE
    TO authenticated
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    )
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 8. Grants
GRANT ALL ON TABLE public.tool_connections TO authenticated, service_role;
GRANT ALL ON TABLE public.discovered_tools TO authenticated, service_role;
GRANT ALL ON TABLE public.tool_invocations TO authenticated, service_role;
