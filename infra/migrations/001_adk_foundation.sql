-- Block 1 Migration: Sovereign ADK Foundation & Row-Level Security
-- Region Constraint: asia-south1 (Mumbai)

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- 3. Consent Logs Table (DPDP Act Sec. 5 & 6)
CREATE TABLE IF NOT EXISTS public.consent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    consent_type VARCHAR(64) NOT NULL, -- 'CORE_CHAT', 'WORKSPACE_INTEGRATION', 'ZOHO_INTEGRATION'
    status VARCHAR(32) NOT NULL,       -- 'GRANTED', 'REVOKED'
    notice_version VARCHAR(32) NOT NULL,
    ip_address_hash VARCHAR(64),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_consent_logs_user_type ON public.consent_logs(user_id, consent_type, created_at DESC);

-- 4. ADK Sessions Table (90-day storage limitation TTL)
CREATE TABLE IF NOT EXISTS public.adk_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    app_name VARCHAR(64) NOT NULL DEFAULT 'workkbot',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (timezone('utc', now()) + INTERVAL '90 days')
);
CREATE INDEX IF NOT EXISTS idx_adk_sessions_user_id ON public.adk_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_adk_sessions_expires_at ON public.adk_sessions(expires_at);

-- 5. ADK Events Table
CREATE TABLE IF NOT EXISTS public.adk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.adk_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_adk_events_session ON public.adk_events(session_id, created_at ASC);

-- 6. Row-Level Security (RLS) Invariants
ALTER TABLE public.consent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE public.adk_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.adk_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.adk_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.adk_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "consent_logs_user_isolation" ON public.consent_logs;
CREATE POLICY "consent_logs_user_isolation" ON public.consent_logs
    FOR ALL USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);

DROP POLICY IF EXISTS "adk_sessions_user_isolation" ON public.adk_sessions;
CREATE POLICY "adk_sessions_user_isolation" ON public.adk_sessions
    FOR ALL USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);

DROP POLICY IF EXISTS "adk_events_user_isolation" ON public.adk_events;
CREATE POLICY "adk_events_user_isolation" ON public.adk_events
    FOR ALL USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
