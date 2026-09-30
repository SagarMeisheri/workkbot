-- Migration: 20260927000003_dsr_erasure.sql
-- Full atomic DSR cascading erasure (Apple Guideline 5.1.1 & DPDP Act 2023)

CREATE OR REPLACE FUNCTION public.execute_dsr_erasure(target_user_id uuid, executing_org_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'vault'
AS $$
BEGIN
    -- 1. Hard-delete episodic ADK sessions and events
    DELETE FROM public.adk_sessions WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.conversations WHERE user_id = target_user_id AND org_id = executing_org_id;

    -- 2. Hard-delete semantic memory and vectors if table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'memory_items') THEN
        DELETE FROM public.memory_items WHERE user_id = target_user_id AND org_id = executing_org_id;
    END IF;

    -- 3. Delete connected MCP tokens and PII vault secrets from Supabase Vault
    DELETE FROM vault.secrets
    WHERE id IN (
        SELECT vault_secret_id
        FROM public.mcp_connections
        WHERE user_id = target_user_id AND org_id = executing_org_id AND vault_secret_id IS NOT NULL
    );
    DELETE FROM public.mcp_connections WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.user_consents WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.ai_content_reports WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.profiles WHERE id = target_user_id AND org_id = executing_org_id;

    -- 4. Pseudonymize tool audit logs if table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tool_invocations') THEN
        UPDATE public.tool_invocations
        SET user_id = NULL,
            arguments = '{"redacted": "DSR_ERASURE_APPLIED"}'::jsonb,
            result = '{"redacted": "DSR_ERASURE_APPLIED"}'::jsonb
        WHERE user_id = target_user_id AND org_id = executing_org_id;
    END IF;

    -- 5. Delete auth user record
    DELETE FROM auth.users WHERE id = target_user_id;

    RETURN jsonb_build_object('status', 'success', 'user_id', target_user_id);
END;
$$;

-- Restrict execution of destructive DSR cascade strictly to backend service_role
REVOKE EXECUTE ON FUNCTION public.execute_dsr_erasure(uuid, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.execute_dsr_erasure(uuid, uuid) TO service_role;

