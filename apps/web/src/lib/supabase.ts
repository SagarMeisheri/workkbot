import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "@workkbot/shared-types";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://jqplgapyplejrixvbgmu.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpxcGxnYXB5cGxlanJpeHZiZ211Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA1NTUyODgsImV4cCI6MjEwNjEzMTI4OH0.eTl1-a4DJp7dH4K0RBBaUbD17iE4nCmpAbdQvCFyjBo";

export const supabase = createBrowserClient<Database>(supabaseUrl, supabaseAnonKey);
