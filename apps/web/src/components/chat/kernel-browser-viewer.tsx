"use client";

import React, { useState } from "react";
import { ExternalLink, X, Monitor, Shield, RefreshCw } from "lucide-react";
import { BACKEND_URL } from "@/lib/config";

interface KernelBrowserViewerProps {
  liveViewUrl: string;
  replayViewUrl?: string;
  taskTitle?: string;
  sessionId?: string;
  onClose: () => void;
  token?: string;
}

export function KernelBrowserViewer({
  liveViewUrl,
  replayViewUrl,
  taskTitle = "Autonomous Cloud Browser Task",
  sessionId,
  onClose,
  token,
}: KernelBrowserViewerProps) {
  const [isIframeLoaded, setIsIframeLoaded] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const [viewMode, setViewMode] = useState<"live" | "replay">("live");

  const handleClose = async () => {
    setIsTerminating(true);
    try {
      if (sessionId) {
        await fetch(`${BACKEND_URL}/api/v1/vm/close`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ session_id: sessionId }),
          keepalive: true,
        });
      }
    } catch (e) {
      console.debug("Kernel session termination ping sent:", e);
    }
    onClose();
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-card rounded-xl border border-border overflow-hidden shadow-sm animate-in fade-in duration-200">
      {/* Top Controls Bar */}
      <div className="h-12 px-4 border-b border-border bg-muted/40 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="flex h-2.5 w-2.5 relative shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
          </span>
          <div className="flex items-center gap-1.5 font-medium text-xs text-foreground truncate">
            <Monitor className="w-3.5 h-3.5 text-primary shrink-0" />
            <span className="font-semibold">Kernel Cloud Browser</span>
            <span className="text-[11px] text-muted-foreground font-mono truncate">
              ({taskTitle})
            </span>
          </div>
          {replayViewUrl ? (
            <div className="flex items-center rounded-lg bg-muted p-0.5 border border-border text-[11px]">
              <button
                onClick={() => setViewMode("live")}
                className={`px-2 py-0.5 rounded-md transition-colors ${
                  viewMode === "live"
                    ? "bg-background text-foreground shadow-xs font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Live View
              </button>
              <button
                onClick={() => setViewMode("replay")}
                className={`px-2 py-0.5 rounded-md transition-colors ${
                  viewMode === "replay"
                    ? "bg-background text-foreground shadow-xs font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Replay Video
              </button>
            </div>
          ) : (
            <span className="hidden sm:inline-flex text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shrink-0">
              Live Stream
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Open in New Tab */}
          <a
            href={viewMode === "replay" && replayViewUrl ? replayViewUrl : liveViewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="h-7 w-7 rounded-md border border-border hover:bg-accent text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors"
            title="Open browser stream in new tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          {/* Close Split View Button */}
          <button
            onClick={handleClose}
            disabled={isTerminating}
            className="h-7 w-7 rounded-md border border-border hover:bg-destructive/10 text-muted-foreground hover:text-destructive flex items-center justify-center transition-colors disabled:opacity-50"
            title="Close Split View"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Embedded Live View / Replay Iframe */}
      <div className="flex-1 w-full bg-neutral-950 relative min-h-0">
        {!isIframeLoaded && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-neutral-400 text-xs z-10 bg-neutral-950">
            <RefreshCw className="w-5 h-5 animate-spin text-primary" />
            <span>
              {viewMode === "replay"
                ? "Loading Kernel session video replay..."
                : "Connecting to Kernel cloud browser live view..."}
            </span>
          </div>
        )}
        <iframe
          key={viewMode}
          src={viewMode === "replay" && replayViewUrl ? replayViewUrl : liveViewUrl}
          className="w-full h-full border-0 bg-neutral-950"
          title="Kernel AI Cloud Browser View"
          allow="autoplay; clipboard-read; clipboard-write; fullscreen"
          onLoad={() => setIsIframeLoaded(true)}
        />
      </div>

      {/* Bottom Status & Info Bar */}
      <div className="px-4 py-2 border-t border-border bg-card flex items-center justify-between text-xs text-muted-foreground shrink-0">
        <div className="flex items-center gap-2 truncate">
          <Shield className="w-3.5 h-3.5 text-primary shrink-0" />
          <span className="truncate">
            Real-time Chromium automation stream over Kernel AI CDP. Zero local browser overhead.
          </span>
        </div>
        {sessionId && (
          <span className="text-[10px] font-mono text-muted-foreground shrink-0 pl-2">
            ID: {sessionId.slice(0, 8)}...
          </span>
        )}
      </div>
    </div>
  );
}
