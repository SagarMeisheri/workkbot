"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Sparkles, ChevronDown, ChevronUp, ArrowRight, CheckCircle2 } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [showReviewerMode, setShowReviewerMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const { error: signInError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          scopes: "openid email profile",
        },
      });
      if (signInError) throw signInError;
    } catch (err: any) {
      setError(err?.message || "Failed to initialize Google sign-in. Ensure Supabase is configured.");
    } finally {
      setLoading(false);
    }
  };

  const handleReviewerLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/reviewer-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "apple-reviewer@workkbot.in",
          password: "ReviewerDemo2026!Secured",
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Reviewer authentication failed");
      }

      const data = await response.json();
      localStorage.setItem("workkbot_token", data.access_token);
      localStorage.setItem(
        "workkbot_auth",
        JSON.stringify({
          user_id: data.user_id,
          email: data.email,
          first_name: "Reviewer",
          org_id: data.org_id,
          role: data.role,
          is_demo: true,
        })
      );
      router.push("/");
    } catch (err: any) {
      setError(err?.message || "Failed to connect to backend for reviewer authentication. Ensure backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fafafa] dark:bg-[#09090b] p-4">
      <div className="w-full max-w-md bg-white dark:bg-[#18181b] border border-border rounded-2xl shadow-xl p-8 flex flex-col items-center">
        {/* Brand Sunburst & Title */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-amber-600 dark:text-amber-500 text-3xl select-none font-serif">✳</span>
          <span className="text-xl font-semibold tracking-tight text-foreground">Workkbot</span>
        </div>
        <p className="text-sm text-muted-foreground text-center mb-8">
          Enterprise AI Workspace for Modern Teams
        </p>

        {error && (
          <div className="w-full mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 text-xs border border-red-200 dark:border-red-900">
            {error}
          </div>
        )}

        {/* Primary Action: Continue with Google Workspace */}
        <button
          onClick={handleGoogleLogin}
          disabled={loading}
          className="w-full h-11 px-4 rounded-xl border border-border bg-white dark:bg-zinc-900 hover:bg-accent text-foreground font-medium text-sm flex items-center justify-center gap-3 transition-colors shadow-xs disabled:opacity-50"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>Continue with Google Workspace</span>
        </button>

        <p className="text-[11px] text-muted-foreground/80 mt-3 text-center">
          Requests minimal identity only (name, email, avatar). Zero drive or mailbox access at sign-in.
        </p>

        {/* DPDP and App Store Reviewer Sandbox Accordion */}
        <div className="w-full mt-8 pt-6 border-t border-border flex flex-col gap-3">
          <button
            onClick={() => setShowReviewerMode(!showReviewerMode)}
            className="flex items-center justify-between text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <Shield className="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
              App Store Reviewer Mode (Apple Guideline 2.1)
            </span>
            {showReviewerMode ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showReviewerMode && (
            <div className="p-4 rounded-xl bg-muted/50 border border-border flex flex-col gap-3 text-xs animate-in fade-in duration-200">
              <div className="flex flex-col gap-1">
                <span className="text-muted-foreground">Reviewer Account:</span>
                <code className="bg-background px-2 py-1 rounded font-mono text-[11px] border border-border">
                  apple-reviewer@workkbot.in
                </code>
              </div>
              <p className="text-muted-foreground text-[11px]">
                Instant sign-in directly into the isolated sandbox organization with pre-configured tools. Bypasses corporate Google SSO and MFA.
              </p>
              <button
                onClick={handleReviewerLogin}
                disabled={loading}
                className="w-full h-9 rounded-lg bg-primary text-primary-foreground font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
              >
                <span>Sign in as Reviewer</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Security & Statutory Notice Badge */}
        <div className="mt-8 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>DPDP Act 2023 Compliant • Hosted in Mumbai (asia-south1)</span>
        </div>
      </div>
    </div>
  );
}
