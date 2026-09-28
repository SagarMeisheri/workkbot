import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://workkbot-local.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "local-anon-key-placeholder";

export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey);
