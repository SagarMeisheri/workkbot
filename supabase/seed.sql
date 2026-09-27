-- Seed Data for Workkbot 2.0 (Day 1)

-- 1. Standard Production SMB Tenant
INSERT INTO public.organizations (id, name, domains, is_demo)
VALUES 
    ('a0000000-0000-0000-0000-000000000001', 'Workkbot SMB India', ARRAY['workkbot.in', 'smbcorp.in'], false)
ON CONFLICT (id) DO NOTHING;

-- 2. Isolated Apple Reviewer Sandbox Tenant (Apple App Store Guideline 2.1)
INSERT INTO public.organizations (id, name, domains, is_demo)
VALUES 
    ('e0000000-0000-0000-0000-000000000002', 'Apple Reviewer Demo Sandbox', ARRAY['workkbot.in', 'apple-review.internal'], true)
ON CONFLICT (id) DO NOTHING;
