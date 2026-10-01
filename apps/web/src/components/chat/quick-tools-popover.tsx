"use client";

import React, { useState, useEffect, useRef } from "react";
import { RefreshCw, ExternalLink, ShieldCheck, Check } from "lucide-react";
import { BACKEND_URL } from "@/lib/config";

export interface QuickToolsPopoverProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenFullHub: () => void;
  user?: any;
  alignDirection?: "up" | "down";
}

interface QuickToolItem {
  id: "google_workspace" | "zoho_workplace" | "slack" | "github" | "notion";
  name: string;
  subtitle: string;
  renderIcon: () => React.ReactNode;
}

const FEATURED_TOOLS: QuickToolItem[] = [
  {
    id: "google_workspace",
    name: "Google Workspace",
    subtitle: "Gmail, Drive, Calendar",
    renderIcon: () => (
      <svg className="w-4 h-4" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
        />
        <path
          fill="#34A853"
          d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"
        />
        <path
          fill="#FBBC05"
          d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
        />
        <path
          fill="#EA4335"
          d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
        />
      </svg>
    ),
  },
  {
    id: "zoho_workplace",
    name: "Zoho Workplace",
    subtitle: "Books GST, CRM, Mail",
    renderIcon: () => (
      <div className="w-4 h-4 rounded bg-red-600 flex items-center justify-center text-[9px] font-black text-white leading-none tracking-tighter">
        Z
      </div>
    ),
  },
  {
    id: "slack",
    name: "Slack",
    subtitle: "Channels & Team DMs",
    renderIcon: () => (
      <svg className="w-4 h-4" viewBox="0 0 24 24">
        <path
          fill="#E01E5A"
          d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.528 2.528 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z"
        />
        <path
          fill="#36C5F0"
          d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z"
        />
        <path
          fill="#2EB67D"
          d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 0 1-2.522 2.521 2.529 2.529 0 0 1-2.521-2.521V2.522A2.528 2.528 0 0 1 15.165 0a2.528 2.528 0 0 1 2.521 2.522v6.312z"
        />
        <path
          fill="#ECB22E"
          d="M15.165 18.956a2.528 2.528 0 0 1 2.521 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.27a2.528 2.528 0 0 1-2.52-2.522 2.527 2.527 0 0 1 2.52-2.521h6.313A2.528 2.528 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.521h-6.313z"
        />
      </svg>
    ),
  },
  {
    id: "github",
    name: "GitHub",
    subtitle: "Repos, PRs, & Issues",
    renderIcon: () => (
      <svg className="w-4 h-4 fill-foreground" viewBox="0 0 24 24">
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
        />
      </svg>
    ),
  },
  {
    id: "notion",
    name: "Notion",
    subtitle: "Pages & Databases",
    renderIcon: () => (
      <div className="w-4 h-4 rounded bg-zinc-900 dark:bg-white flex items-center justify-center text-[10px] font-bold text-white dark:text-zinc-900 leading-none">
        N
      </div>
    ),
  },
];

export function QuickToolsPopover({
  isOpen,
  onClose,
  onOpenFullHub,
  user,
  alignDirection = "down",
}: QuickToolsPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [activeConnections, setActiveConnections] = useState<any[]>([]);
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);

  const fetchConnections = async () => {
    try {
      const token = user?.access_token || localStorage.getItem("workkbot_token");
      if (!token) return;
      const res = await fetch(`${BACKEND_URL}/api/v1/auth/connectors`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveConnections(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error("QuickToolsPopover: fetchConnections failed", e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchConnections();
    }
    const handleAuthMessage = (event: MessageEvent) => {
      if (event.data?.type === "WORKKBOT_CONNECTOR_CONNECTED") {
        fetchConnections();
        setLoadingProvider(null);
      }
    };
    window.addEventListener("message", handleAuthMessage);
    return () => {
      window.removeEventListener("message", handleAuthMessage);
    };
  }, [isOpen]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleToggle = async (toolId: QuickToolItem["id"], isCurrentlyConnected: boolean) => {
    const token = user?.access_token || localStorage.getItem("workkbot_token");
    if (!token) {
      alert("Please sign in first to manage tools.");
      return;
    }

    setLoadingProvider(toolId);

    if (isCurrentlyConnected) {
      // Disconnect
      try {
        const res = await fetch(`${BACKEND_URL}/api/v1/auth/connectors/${toolId}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok || res.status === 200) {
          setActiveConnections((prev) => prev.filter((c) => c.provider !== toolId && c.id !== toolId));
        }
      } catch (err) {
        console.error("Failed to disconnect connector:", err);
      } finally {
        setLoadingProvider(null);
      }
    } else {
      // Connect: Request authorization URL
      try {
        const authRes = await fetch(
          `${BACKEND_URL}/api/v1/auth/connectors/oauth/authorize?provider=${toolId}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        if (authRes.ok) {
          const authData = await authRes.json();
          if (authData.authorization_url) {
            const width = 600;
            const height = 700;
            const left = window.screenX + (window.outerWidth - width) / 2;
            const top = window.screenY + (window.outerHeight - height) / 2;
            const popup = window.open(
              authData.authorization_url,
              `Connect ${toolId}`,
              `width=${width},height=${height},left=${left},top=${top},status=no,toolbar=no,menubar=no`
            );
            if (!popup) {
              setLoadingProvider(null);
            }
          } else {
            // Direct mock/sandbox connection
            fetchConnections();
            setLoadingProvider(null);
          }
        } else {
          setLoadingProvider(null);
        }
      } catch (err) {
        console.error("Failed to initiate connector auth:", err);
        setLoadingProvider(null);
      }
    }
  };

  const activeCount = FEATURED_TOOLS.filter((t) =>
    activeConnections.some((c) => c.provider === t.id)
  ).length;

  return (
    <div
      ref={popoverRef}
      className={`absolute ${
        alignDirection === "up" ? "bottom-full mb-2" : "top-full mt-2"
      } left-0 w-72 rounded-2xl border border-border bg-popover text-popover-foreground shadow-2xl z-50 overflow-hidden animate-in fade-in ${
        alignDirection === "up" ? "slide-in-from-bottom-2" : "slide-in-from-top-2"
      } duration-150`}
    >
      {/* Header */}
      <div className="px-3.5 py-2.5 border-b border-border/80 flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-foreground">Tools</span>
          <span className="px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 text-[10px] font-medium border border-emerald-500/20">
            {activeCount} active
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-600" />
          <span>Vault Sealed</span>
        </span>
      </div>

      {/* 5 MCP Tool Items with Switches */}
      <div className="p-1.5 flex flex-col gap-1">
        {FEATURED_TOOLS.map((tool) => {
          const isConnected = activeConnections.some((c) => c.provider === tool.id);
          const isLoading = loadingProvider === tool.id;

          return (
            <div
              key={tool.id}
              className="flex items-center justify-between px-2.5 py-2 rounded-xl hover:bg-accent/60 transition-colors"
            >
              {/* Tool Icon & Info */}
              <div className="flex items-center gap-2.5 min-w-0 pr-2">
                <div className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center shrink-0 border border-border/60">
                  {tool.renderIcon()}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-medium text-foreground truncate">{tool.name}</span>
                  <span className="text-[10px] text-muted-foreground truncate">{tool.subtitle}</span>
                </div>
              </div>

              {/* iOS / macOS Styled Toggle Switch */}
              <button
                type="button"
                role="switch"
                aria-checked={isConnected}
                disabled={isLoading}
                onClick={() => handleToggle(tool.id, isConnected)}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none disabled:opacity-50 ${
                  isConnected ? "bg-emerald-600 dark:bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-700"
                }`}
                title={isConnected ? `Disconnect ${tool.name}` : `Connect ${tool.name}`}
              >
                <span
                  className={`pointer-events-none inline-flex items-center justify-center h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    isConnected ? "translate-x-4" : "translate-x-0"
                  }`}
                >
                  {isLoading && (
                    <RefreshCw className="w-2.5 h-2.5 text-zinc-600 animate-spin" />
                  )}
                </span>
              </button>
            </div>
          );
        })}
      </div>

      {/* Footer Deep-link */}
      <div className="px-3.5 py-2 border-t border-border/70 bg-muted/20 flex items-center justify-between text-[11px]">
        <button
          onClick={() => {
            onClose();
            onOpenFullHub();
          }}
          className="text-xs font-medium text-primary hover:underline flex items-center gap-1 transition-colors"
        >
          <span>More connectors & custom MCP</span>
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
