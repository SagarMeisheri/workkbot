-- Migration: 20260927000002_dsr_erasure.sql
-- In-app account deletion & atomic DSR erasure function (Apple Guideline 5.1.1 & DPDP Act 2023)

CREATE OR REPLACE FUNCTION public.execute_dsr_erasure(target_user_id uuid, executing_org_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'vault'
AS $$
BEGIN
    -- 1. Delete associated Vault secrets for user's MCP connections
    DELETE FROM vault.secrets
    WHERE id IN (
        SELECT vault_secret_id
        FROM public.mcp_connections
        WHERE user_id = target_user_id AND org_id = executing_org_id AND vault_secret_id IS NOT NULL
    );

    -- 2. Delete user profiles, consents, mcp_connections
    DELETE FROM public.mcp_connections WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.user_consents WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.profiles WHERE id = target_user_id AND org_id = executing_org_id;
    
    -- 3. Delete auth user record
    DELETE FROM auth.users WHERE id = target_user_id;
    
    RETURN jsonb_build_object('status', 'success', 'user_id', target_user_id);
END;
$$;
