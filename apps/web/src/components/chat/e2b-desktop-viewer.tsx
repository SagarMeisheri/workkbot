"use client";

import React, { useState } from "react";
import { ExternalLink, CheckCircle, RefreshCw, X, Shield, Monitor } from "lucide-react";
import { BACKEND_URL } from "@/lib/config";

interface E2BDesktopViewerProps {
  streamUrl: string;
  sessionId?: string;
  isLoggedIn?: boolean;
  pendingItem?: {
    name?: string;
    selling_price?: number;
    cost_price?: number;
    unit?: string;
    type?: string;
  } | null;
  onClose: () => void;
  onLoginConfirmed: (result: any) => void;
  token?: string;
}

export function E2BDesktopViewer({
  streamUrl,
  sessionId,
  isLoggedIn = false,
  pendingItem,
  onClose,
  onLoginConfirmed,
  token,
}: E2BDesktopViewerProps) {
  const [loading, setLoading] = useState(false);
  const [localLoggedIn, setLocalLoggedIn] = useState(isLoggedIn);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleConfirmLogin = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/vm/confirm-login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: sessionId,
          pending_item: pendingItem,
        }),
      });

      if (!res.ok) {
        throw new Error(`Failed to confirm login (HTTP ${res.status})`);
      }

      const data = await res.json();
      setLocalLoggedIn(true);
      onLoginConfirmed(data);
    } catch (e: any) {
      console.error("Error confirming login:", e);
      setErrorMsg(e.message || "Failed to resume item creation");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = async () => {
    try {
      if (sessionId) {
        fetch(`${BACKEND_URL}/api/v1/vm/close`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ session_id: sessionId }),
          keepalive: true,
        }).catch(() => {});
      }
    } catch {
      // ignore
    }
    onClose();
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-card rounded-xl border border-border overflow-hidden shadow-sm">
      {/* Top Controls Bar */}
      <div className="h-12 px-4 border-b border-border bg-muted/40 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
          </span>
          <div className="flex items-center gap-1.5 font-medium text-xs text-foreground">
            <Monitor className="w-3.5 h-3.5 text-primary" />
            <span>Cloud Browser (Kernel)</span>
            <span className="text-[11px] text-muted-foreground font-mono">
              (Zoho Books)
            </span>
          </div>
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
              localLoggedIn
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
            }`}
          >
            {localLoggedIn ? "Ready & Authenticated" : "Awaiting Login"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Proceed Button */}
          {!localLoggedIn ? (
            <button
              onClick={handleConfirmLogin}
              disabled={loading}
              className="h-7 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 flex items-center gap-1.5 transition-all shadow-xs disabled:opacity-50"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{loading ? "Creating Item..." : "I Have Logged In - Proceed"}</span>
            </button>
          ) : (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Connected</span>
            </span>
          )}

          {/* Open in New Tab */}
          <a
            href={streamUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="h-7 w-7 rounded-md border border-border hover:bg-accent text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors"
            title="Open stream in new tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          {/* Close Split View */}
          <button
            onClick={handleClose}
            className="h-7 w-7 rounded-md border border-border hover:bg-accent text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors"
            title="Close Split View and terminate VM sandbox"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Target Pending Item Banner */}
      {pendingItem && pendingItem.name && (
        <div className="px-4 py-2 bg-primary/5 border-b border-border/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 truncate">
            <span className="font-semibold text-primary">Pending Item:</span>
            <span className="font-medium text-foreground">{pendingItem.name}</span>
            {pendingItem.selling_price && (
              <span className="text-muted-foreground">
                (Sell: ₹{pendingItem.selling_price}
                {pendingItem.cost_price ? ` / Cost: ₹${pendingItem.cost_price}` : ""})
              </span>
            )}
          </div>
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
            Auto-Fill on Login
          </span>
        </div>
      )}

      {errorMsg && (
        <div className="px-4 py-1.5 bg-destructive/10 text-destructive text-xs border-b border-destructive/20">
          {errorMsg}
        </div>
      )}

      {/* Embedded Live Desktop Frame */}
      <div className="flex-1 w-full bg-neutral-950 relative min-h-0">
        <iframe
          src={streamUrl}
          className="w-full h-full border-0"
          title="E2B Desktop Live Stream"
          allow="clipboard-read; clipboard-write; fullscreen"
        />
      </div>

      {/* Bottom Instructions Banner */}
      <div className="p-3 border-t border-border bg-card flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-primary" />
          <span>
            {localLoggedIn
              ? "Agent has access to Zoho Books. Actions are executed through sandboxed computer use."
              : "Log in with your Zoho account above. Once on the dashboard, click 'I Have Logged In - Proceed'."}
          </span>
        </div>
      </div>
    </div>
  );
}
