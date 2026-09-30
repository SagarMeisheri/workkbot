"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { BACKEND_URL } from "@/lib/config";

const TOOLKIT_TO_PROVIDER: Record<string, string> = {
  gmail: "google_workspace",
  googlecalendar: "google_workspace",
  googledrive: "google_workspace",
  google_workspace: "google_workspace",
  zoho: "zoho_workplace",
  zohocrm: "zoho_workplace",
  zohobooks: "zoho_workplace",
  zoho_workplace: "zoho_workplace",
  notion: "notion",
  slack: "slack",
  jira: "atlassian",
  atlassian: "atlassian",
  canva: "canva",
  figma: "figma",
  hubspot: "hubspot",
  github: "github",
  linear: "linear",
};

function CallbackContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const authStatus = searchParams.get("status") || "success";
        const connectedAccountId = searchParams.get("connected_account_id") || searchParams.get("id");
        const rawProvider = searchParams.get("provider") || searchParams.get("toolkit") || "composio";
        const provider = TOOLKIT_TO_PROVIDER[rawProvider] || rawProvider;
        const token = localStorage.getItem("workkbot_token");

        if (authStatus === "failed") {
          setStatus("error");
          setErrorMessage("Authentication was cancelled or failed by the provider.");
          return;
        }

        if (token) {
          await fetch(`${BACKEND_URL}/api/v1/auth/connectors/oauth/callback`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              provider,
              connected_account_id: connectedAccountId,
              status: "active",
            }),
          });
        }

        setStatus("success");

        // Notify parent window (Connectors modal)
        if (window.opener) {
          window.opener.postMessage(
            {
              type: "COMPOSIO_AUTH_SUCCESS",
              provider,
              connected_account_id: connectedAccountId,
            },
            "*"
          );
          setTimeout(() => {
            window.close();
          }, 1200);
        }
      } catch (err: any) {
        console.error("Composio callback error:", err);
        setStatus("error");
        setErrorMessage(err.message || "Failed to finalize connector authentication.");
      }
    };

    handleCallback();
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-card border border-border rounded-2xl p-6 shadow-xl text-center flex flex-col items-center">
        {status === "loading" && (
          <>
            <RefreshCw className="w-10 h-10 text-primary animate-spin mb-4" />
            <h2 className="text-lg font-semibold text-foreground">Securing Connection...</h2>
            <p className="text-xs text-muted-foreground mt-1">
              Finalizing credentials and encrypting keys in Supabase Vault.
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-600 mb-4 animate-in zoom-in-50 duration-200">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">Connected Successfully</h2>
            <p className="text-xs text-muted-foreground mt-1">
              Your account has been connected via Composio and hardware-sealed in Supabase Vault.
            </p>
            <p className="text-[11px] text-muted-foreground/80 mt-3 font-mono">
              Closing this window...
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950 flex items-center justify-center text-red-600 mb-4">
              <AlertCircle className="w-7 h-7" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">Connection Failed</h2>
            <p className="text-xs text-red-500 mt-1">{errorMessage}</p>
            <button
              onClick={() => (window.opener ? window.close() : (window.location.href = "/"))}
              className="mt-4 px-4 py-2 rounded-xl bg-muted text-foreground text-xs font-medium hover:bg-muted/80 transition-colors"
            >
              Close Window
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function ConnectorsCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <RefreshCw className="w-8 h-8 text-muted-foreground animate-spin" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
