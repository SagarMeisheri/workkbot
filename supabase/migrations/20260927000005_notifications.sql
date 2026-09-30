-- Migration: 20260927000005_notifications.sql
-- Description: User notifications table with Supabase Realtime replication (Spec 05)

CREATE TABLE IF NOT EXISTS public.user_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'general' CHECK (type IN ('hitl_approval', 'tool_completed', 'security_alert', 'general')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    action_url TEXT,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for efficient lookup
CREATE INDEX IF NOT EXISTS idx_user_notifications_user ON public.user_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_org ON public.user_notifications(org_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_created ON public.user_notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_notifications_unread ON public.user_notifications(user_id) WHERE read_at IS NULL;

-- Enable Row-Level Security
ALTER TABLE public.user_notifications ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own notifications"
    ON public.user_notifications
    FOR SELECT
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can insert own notifications"
    ON public.user_notifications
    FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

CREATE POLICY "Users can update own notifications"
    ON public.user_notifications
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

CREATE POLICY "Users can delete own notifications"
    ON public.user_notifications
    FOR DELETE
    TO authenticated
    USING (
        user_id = (SELECT auth.uid())
        AND org_id = (SELECT org_id FROM public.profiles WHERE id = (SELECT auth.uid()))
    );

-- Enable Realtime Replication
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'user_notifications'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.user_notifications;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        NULL;
END $$;
