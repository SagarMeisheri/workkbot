-- Migration: 20260928000002_fix_rls_recursion.sql
-- Description: Resolves PostgreSQL Error 42P17 (infinite recursion in profiles) via SECURITY DEFINER and JWT claims

-- 1. Create a hardened SECURITY DEFINER helper function to lookup org_id without RLS recursion
CREATE OR REPLACE FUNCTION public.get_auth_user_org_id(user_uuid uuid DEFAULT auth.uid())
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT org_id FROM public.profiles WHERE id = user_uuid LIMIT 1;
$$;

-- Grant execute to authenticated and anon
GRANT EXECUTE ON FUNCTION public.get_auth_user_org_id(uuid) TO authenticated, anon, service_role;

-- 2. Fix profiles policies to prevent self-referential circular recursion
DROP POLICY IF EXISTS "Users can view profiles in their organization" ON public.profiles;
CREATE POLICY "Users can view profiles in their organization"
    ON public.profiles
    FOR SELECT
    USING (
        id = auth.uid()
        OR org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 3. Fix organizations policies
DROP POLICY IF EXISTS "Users can view their organization" ON public.organizations;
CREATE POLICY "Users can view their organization"
    ON public.organizations
    FOR SELECT
    USING (
        id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 4. Fix conversations policies
DROP POLICY IF EXISTS "Users can view own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON public.conversations;

CREATE POLICY "Users can view own conversations"
    ON public.conversations
    FOR SELECT
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can insert own conversations"
    ON public.conversations
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can update own conversations"
    ON public.conversations
    FOR UPDATE
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can delete own conversations"
    ON public.conversations
    FOR DELETE
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 5. Fix adk_sessions policies
DROP POLICY IF EXISTS "Users can view own adk sessions" ON public.adk_sessions;
DROP POLICY IF EXISTS "Users can insert own adk sessions" ON public.adk_sessions;
DROP POLICY IF EXISTS "Users can update own adk sessions" ON public.adk_sessions;
DROP POLICY IF EXISTS "Users can delete own adk sessions" ON public.adk_sessions;

CREATE POLICY "Users can view own adk sessions"
    ON public.adk_sessions
    FOR SELECT
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can insert own adk sessions"
    ON public.adk_sessions
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can update own adk sessions"
    ON public.adk_sessions
    FOR UPDATE
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can delete own adk sessions"
    ON public.adk_sessions
    FOR DELETE
    USING (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

-- 6. Fix adk_events policies and widen author constraint
DROP POLICY IF EXISTS "Users can view own adk events" ON public.adk_events;
DROP POLICY IF EXISTS "Users can insert own adk events" ON public.adk_events;
DROP POLICY IF EXISTS "Users can delete own adk events" ON public.adk_events;

CREATE POLICY "Users can view own adk events"
    ON public.adk_events
    FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM public.adk_sessions
            WHERE user_id = auth.uid()
            AND org_id = COALESCE(
                NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
                (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
                public.get_auth_user_org_id()
            )
        )
    );

CREATE POLICY "Users can insert own adk events"
    ON public.adk_events
    FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM public.adk_sessions
            WHERE user_id = auth.uid()
            AND org_id = COALESCE(
                NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
                (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
                public.get_auth_user_org_id()
            )
        )
    );

CREATE POLICY "Users can delete own adk events"
    ON public.adk_events
    FOR DELETE
    USING (
        session_id IN (
            SELECT id FROM public.adk_sessions
            WHERE user_id = auth.uid()
            AND org_id = COALESCE(
                NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
                (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
                public.get_auth_user_org_id()
            )
        )
    );

ALTER TABLE public.adk_events DROP CONSTRAINT IF EXISTS adk_events_author_check;
ALTER TABLE public.adk_events ADD CONSTRAINT adk_events_author_check 
    CHECK (author IN ('user', 'model', 'system', 'workkbot_core'));

-- 7. Fix ai_content_reports policies
DROP POLICY IF EXISTS "Users can insert content reports" ON public.ai_content_reports;
DROP POLICY IF EXISTS "Users can view own content reports" ON public.ai_content_reports;

CREATE POLICY "Users can insert content reports"
    ON public.ai_content_reports
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        )
    );

CREATE POLICY "Users can view own content reports"
    ON public.ai_content_reports
    FOR SELECT
    USING (
        (user_id = auth.uid() AND org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        ))
        OR (org_id = COALESCE(
            NULLIF(current_setting('request.jwt.claim.org_id', true), '')::uuid,
            (auth.jwt() -> 'app_metadata' ->> 'org_id')::uuid,
            public.get_auth_user_org_id()
        ) AND EXISTS (
            SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('org-admin', 'tool-admin')
        ))
    );
