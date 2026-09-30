-- Migration: 20260927000004_mcp_tools_and_vault.sql
-- Description: Spec 04 Sovereign Remote MCP Tools, Supabase Vault & In-Chat HITL Audit Trail

-- 1. Ensure public.mcp_connections has unique constraint and updated status checks
DO $$
BEGIN
    -- Ensure UNIQUE constraint on (user_id, provider)
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_mcp_connections_user_provider'
    ) THEN
        ALTER TABLE public.mcp_connections 
        ADD CONSTRAINT uq_mcp_connections_user_provider UNIQUE (user_id, provider);
    END IF;

    -- Update status check constraint to include 'connecting'
    ALTER TABLE public.mcp_connections DROP CONSTRAINT IF EXISTS mcp_connections_status_check;
    ALTER TABLE public.mcp_connections ADD CONSTRAINT mcp_connections_status_check 
        CHECK (status IN ('active', 'expired', 'revoked', 'connecting'));
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Constraint update on mcp_connections completed or skipped: %', SQLERRM;
END $$;

-- Policies for mcp_connections write operations
DROP POLICY IF EXISTS "Users can insert own mcp connections" ON public.mcp_connections;
CREATE POLICY "Users can insert own mcp connections"
    ON public.mcp_connections
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update own mcp connections" ON public.mcp_connections;
CREATE POLICY "Users can update own mcp connections"
    ON public.mcp_connections
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete own mcp connections" ON public.mcp_connections;
CREATE POLICY "Users can delete own mcp connections"
    ON public.mcp_connections
    FOR DELETE
    USING (user_id = auth.uid());

-- 2. Create public.tool_invocations audit log table
CREATE TABLE IF NOT EXISTS public.tool_invocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    execution_duration_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'blocked_hitl', 'declined_hitl')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_tool_invocations_user_org 
    ON public.tool_invocations(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_session 
    ON public.tool_invocations(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_created_at 
    ON public.tool_invocations(created_at DESC);

-- Enable RLS on public.tool_invocations
ALTER TABLE public.tool_invocations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own tool invocations" ON public.tool_invocations;
CREATE POLICY "Users can view own tool invocations"
    ON public.tool_invocations
    FOR SELECT
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can insert own tool invocations" ON public.tool_invocations;
CREATE POLICY "Users can insert own tool invocations"
    ON public.tool_invocations
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- 3. Supabase Vault Helper Functions (RPC)
CREATE OR REPLACE FUNCTION public.create_vault_secret(
    p_secret TEXT,
    p_name TEXT,
    p_description TEXT DEFAULT ''
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_secret_id UUID;
BEGIN
    -- If vault schema exists (Supabase cloud), insert into vault.secrets
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'vault' AND table_name = 'secrets') THEN
        INSERT INTO vault.secrets (secret, name, description)
        VALUES (p_secret, p_name, p_description)
        RETURNING id INTO v_secret_id;
        RETURN v_secret_id;
    ELSE
        -- Fallback pseudo-id when vault extension is not active locally
        RETURN gen_random_uuid();
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_decrypted_vault_secret(
    p_secret_id UUID
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_secret TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'vault' AND table_name = 'decrypted_secrets') THEN
        SELECT decrypted_secret INTO v_secret
        FROM vault.decrypted_secrets
        WHERE id = p_secret_id;
        RETURN v_secret;
    ELSE
        RETURN NULL;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.delete_vault_secret(
    p_secret_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'vault' AND table_name = 'secrets') THEN
        DELETE FROM vault.secrets WHERE id = p_secret_id;
        RETURN TRUE;
    ELSE
        RETURN TRUE;
    END IF;
END;
$$;
