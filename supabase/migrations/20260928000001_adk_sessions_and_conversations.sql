-- Migration: 20260928000001_adk_sessions_and_conversations.sql
-- Description: Core tables for Conversations, Google ADK Sessions, Event Trees, AI Moderation Reports (Apple 1.2) & RLS

-- 1. Conversations Summary Table
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New chat',
    summary TEXT,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    pinned BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user_org ON public.conversations(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON public.conversations(updated_at DESC);

-- 2. ADK Sessions Table (Google ADK DatabaseSessionService integration)
CREATE TABLE IF NOT EXISTS public.adk_sessions (
    id TEXT PRIMARY KEY,
    app_name TEXT NOT NULL DEFAULT 'workkbot_core',
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_adk_sessions_user_org ON public.adk_sessions(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_adk_sessions_conv ON public.adk_sessions(conversation_id);

-- 3. ADK Events Table (Multi-turn event tree with parent checkpoint branching)
CREATE TABLE IF NOT EXISTS public.adk_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES public.adk_sessions(id) ON DELETE CASCADE,
    invocation_id TEXT,
    parent_event_id TEXT,
    branch TEXT NOT NULL DEFAULT 'main',
    author TEXT NOT NULL CHECK (author IN ('user', 'model', 'system')),
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    actions JSONB DEFAULT '{}'::jsonb,
    turn_complete BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_adk_events_session ON public.adk_events(session_id);
CREATE INDEX IF NOT EXISTS idx_adk_events_parent ON public.adk_events(parent_event_id);
CREATE INDEX IF NOT EXISTS idx_adk_events_created_at ON public.adk_events(created_at ASC);

-- 4. AI Content Moderation Reports (Apple App Store Guideline 1.2 Compliance)
CREATE TABLE IF NOT EXISTS public.ai_content_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    session_id TEXT,
    message_id TEXT NOT NULL,
    content_snapshot TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('inaccurate', 'offensive', 'pii_leak', 'copyright', 'other')),
    details TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'investigating', 'resolved', 'dismissed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_content_reports_user_org ON public.ai_content_reports(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_ai_content_reports_created_at ON public.ai_content_reports(created_at DESC);

-- 5. Enable Row-Level Security (RLS) on all new tables
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.adk_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.adk_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_content_reports ENABLE ROW LEVEL SECURITY;

-- 6. RLS Policies

-- Conversations: Tenant & User isolation
CREATE POLICY "Users can view own conversations"
    ON public.conversations
    FOR SELECT
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can insert own conversations"
    ON public.conversations
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can update own conversations"
    ON public.conversations
    FOR UPDATE
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can delete own conversations"
    ON public.conversations
    FOR DELETE
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

-- ADK Sessions: Isolated per user and tenant
CREATE POLICY "Users can view own adk sessions"
    ON public.adk_sessions
    FOR SELECT
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can insert own adk sessions"
    ON public.adk_sessions
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can update own adk sessions"
    ON public.adk_sessions
    FOR UPDATE
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can delete own adk sessions"
    ON public.adk_sessions
    FOR DELETE
    USING (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

-- ADK Events: Accessible only if session belongs to user
CREATE POLICY "Users can view own adk events"
    ON public.adk_events
    FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM public.adk_sessions
            WHERE user_id = auth.uid()
            AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
        )
    );

CREATE POLICY "Users can insert own adk events"
    ON public.adk_events
    FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM public.adk_sessions
            WHERE user_id = auth.uid()
            AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
        )
    );

CREATE POLICY "Users can delete own adk events"
    ON public.adk_events
    FOR DELETE
    USING (
        session_id IN (
            SELECT id FROM public.adk_sessions
            WHERE user_id = auth.uid()
            AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
        )
    );

-- AI Content Reports: Users can create and view their reports; org admins can view all tenant reports
CREATE POLICY "Users can insert content reports"
    ON public.ai_content_reports
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can view own content reports"
    ON public.ai_content_reports
    FOR SELECT
    USING (
        (user_id = auth.uid() AND org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid()))
        OR (org_id = (SELECT org_id FROM public.profiles WHERE id = auth.uid() AND role IN ('org-admin', 'tool-admin')))
    );

-- 7. Update Atomic DSR Erasure Procedure (Cascading deletion across conversations, sessions, events, reports)
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

    -- 2. Delete user AI moderation reports
    DELETE FROM public.ai_content_reports WHERE user_id = target_user_id AND org_id = executing_org_id;

    -- 3. Delete user ADK events (via sessions CASCADE) and ADK sessions
    DELETE FROM public.adk_sessions WHERE user_id = target_user_id AND org_id = executing_org_id;

    -- 4. Delete user conversations
    DELETE FROM public.conversations WHERE user_id = target_user_id AND org_id = executing_org_id;

    -- 5. Delete user profiles, consents, mcp_connections
    DELETE FROM public.mcp_connections WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.user_consents WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.profiles WHERE id = target_user_id AND org_id = executing_org_id;
    
    -- 6. Delete auth user record
    DELETE FROM auth.users WHERE id = target_user_id;
    
    RETURN jsonb_build_object('status', 'success', 'user_id', target_user_id);
END;
$$;
