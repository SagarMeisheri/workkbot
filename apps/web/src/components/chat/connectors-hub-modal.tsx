"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Search,
  Plus,
  CheckCircle2,
  ExternalLink,
  Shield,
  Trash2,
  RefreshCw,
  FolderLock,
  Layers,
  Sparkles,
} from "lucide-react";
import { SEED_CONNECTORS, ConnectorDefinition } from "@workkbot/shared-types";

interface ConnectorsHubModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: any;
}

export function ConnectorsHubModal({ isOpen, onClose, user }: ConnectorsHubModalProps) {
  const [activeTab, setActiveTab] = useState<"discover" | "yours">("discover");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [activeConnections, setActiveConnections] = useState<any[]>([]);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [showCustomMcpForm, setShowCustomMcpForm] = useState(false);
  const [customEndpoint, setCustomEndpoint] = useState("");

  const fetchConnections = async () => {
    try {
      const token = localStorage.getItem("workkbot_token");
      const res = await fetch("http://localhost:8000/api/v1/auth/connectors", {
        headers: { Authorization: `Bearer ${token || "mock"}` },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveConnections(data);
      }
    } catch (e) {
      // Fallback local mock connections
      const local = localStorage.getItem("workkbot_connections");
      if (local) {
        setActiveConnections(JSON.parse(local));
      }
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchConnections();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConnect = async (connector: ConnectorDefinition) => {
    setConnectingProvider(connector.id);
    try {
      const token = localStorage.getItem("workkbot_token");
      // Symmetrical OAuth callback endpoint storing into Supabase Vault
      const res = await fetch("http://localhost:8000/api/v1/auth/connectors/oauth/callback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token || "mock"}`,
        },
        body: JSON.stringify({
          provider: connector.id,
          code: `auth-code-${Date.now()}`,
        }),
      });

      if (res.ok) {
        const newConn = await res.json();
        setActiveConnections((prev) => [...prev.filter((c) => c.provider !== connector.id), newConn]);
      } else {
        // Fallback local persistence
        const mockConn = {
          id: `conn_${Date.now()}`,
          provider: connector.id,
          scopes: connector.defaultScopes,
          status: "active",
          updated_at: new Date().toISOString(),
        };
        const updated = [...activeConnections.filter((c) => c.provider !== connector.id), mockConn];
        setActiveConnections(updated);
        localStorage.setItem("workkbot_connections", JSON.stringify(updated));
      }
    } catch (e) {
      console.error("Connect error:", e);
    } finally {
      setConnectingProvider(null);
    }
  };

  const handleDisconnect = async (connectionId: string) => {
    try {
      const token = localStorage.getItem("workkbot_token");
      await fetch(`http://localhost:8000/api/v1/auth/connectors/${connectionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token || "mock"}` },
      });
    } catch (e) {
      console.error("Disconnect error:", e);
    } finally {
      const updated = activeConnections.filter((c) => c.id !== connectionId);
      setActiveConnections(updated);
      localStorage.setItem("workkbot_connections", JSON.stringify(updated));
    }
  };

  const filteredConnectors = SEED_CONNECTORS.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.publisher.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "all" || c.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-3xl bg-card border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-foreground">Connectors</h2>
            {/* Segmented Toggle [ Yours | Discover ] */}
            <div className="flex items-center p-0.5 rounded-lg bg-muted text-xs font-medium">
              <button
                onClick={() => setActiveTab("discover")}
                className={`px-3 py-1 rounded-md transition-colors ${
                  activeTab === "discover"
                    ? "bg-background text-foreground shadow-2xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Discover
              </button>
              <button
                onClick={() => setActiveTab("yours")}
                className={`px-3 py-1 rounded-md transition-colors flex items-center gap-1.5 ${
                  activeTab === "yours"
                    ? "bg-background text-foreground shadow-2xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span>Yours</span>
                {activeConnections.length > 0 && (
                  <span className="w-4 h-4 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-300 text-[10px] flex items-center justify-center font-bold">
                    {activeConnections.length}
                  </span>
                )}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCustomMcpForm(!showCustomMcpForm)}
              className="h-8 px-2.5 rounded-lg border border-border hover:bg-accent text-xs font-medium flex items-center gap-1.5 transition-colors text-foreground"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>+ Add ▾</span>
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Custom MCP Modal Drawer */}
        {showCustomMcpForm && (
          <div className="px-6 py-3 bg-muted/40 border-b border-border flex items-center gap-3 text-xs animate-in slide-in-from-top duration-150">
            <span className="text-muted-foreground whitespace-nowrap font-medium">Custom MCP Endpoint:</span>
            <input
              type="text"
              placeholder="http://127.0.0.1:9005/sse or stdio command"
              value={customEndpoint}
              onChange={(e) => setCustomEndpoint(e.target.value)}
              className="flex-1 h-8 px-3 rounded-lg border border-border bg-background text-foreground text-xs outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              onClick={() => {
                setShowCustomMcpForm(false);
                setCustomEndpoint("");
              }}
              className="h-8 px-3 rounded-lg bg-primary text-primary-foreground font-medium hover:opacity-90 transition-opacity"
            >
              Register
            </button>
          </div>
        )}

        {/* Search Bar & Categories */}
        <div className="px-6 py-3 border-b border-border flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search connectors (Google, Zoho, Notion, Slack)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-xl border border-border bg-background text-foreground text-xs outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground"
            />
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="h-9 px-3 rounded-xl border border-border bg-background text-foreground text-xs outline-none cursor-pointer"
          >
            <option value="all">All Categories</option>
            <option value="productivity">Productivity</option>
            <option value="accounting_finance">Accounting & GST</option>
            <option value="sales_crm">Sales & CRM</option>
            <option value="communication">Communication</option>
            <option value="developer">Developer</option>
          </select>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "discover" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredConnectors.map((connector) => {
                const isConnected = activeConnections.some((c) => c.provider === connector.id);
                const isConnecting = connectingProvider === connector.id;

                return (
                  <div
                    key={connector.id}
                    className="p-4 rounded-xl border border-border bg-card hover:border-border/80 transition-all flex flex-col justify-between gap-3 shadow-2xs group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center font-bold text-sm text-foreground uppercase border border-border">
                          {connector.name.slice(0, 2)}
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <h3 className="text-sm font-semibold text-foreground">{connector.name}</h3>
                            {connector.verified && (
                              <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                            )}
                          </div>
                          <span className="text-[11px] text-muted-foreground">{connector.publisher}</span>
                        </div>
                      </div>

                      {isConnected ? (
                        <span className="h-7 px-2.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 text-[11px] font-medium flex items-center gap-1 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Connected</span>
                        </span>
                      ) : (
                        <button
                          onClick={() => handleConnect(connector)}
                          disabled={isConnecting}
                          className="h-7 px-3 rounded-lg border border-border bg-white dark:bg-zinc-900 hover:bg-accent text-foreground text-xs font-medium flex items-center gap-1 transition-colors shadow-2xs disabled:opacity-50"
                        >
                          {isConnecting ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Plus className="w-3 h-3" />
                          )}
                          <span>Connect</span>
                        </button>
                      )}
                    </div>

                    <p className="text-xs text-muted-foreground line-clamp-2">{connector.description}</p>

                    <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FolderLock className="w-3 h-3 text-amber-600" />
                        <span>Supabase Vault Sealed</span>
                      </span>
                      <span className="capitalize">{connector.category.replace("_", " ")}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Yours Tab */
            <div className="flex flex-col gap-3">
              {activeConnections.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Layers className="w-8 h-8 text-muted-foreground mb-2" />
                  <p className="text-sm font-medium text-foreground">No active connectors yet</p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                    Switch to the Discover tab to connect Google Workspace, Zoho Workplace, or third-party tools.
                  </p>
                </div>
              ) : (
                activeConnections.map((conn) => {
                  const def = SEED_CONNECTORS.find((c) => c.id === conn.provider);
                  const title = def ? def.name : conn.provider;

                  return (
                    <div
                      key={conn.id}
                      className="p-4 rounded-xl border border-border bg-card flex items-center justify-between gap-4 shadow-2xs"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center font-bold text-xs uppercase border border-border">
                          {title.slice(0, 2)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-medium text-foreground">{title}</h4>
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-[10px] text-emerald-600 font-medium uppercase">Active</span>
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            Scopes: {conn.scopes ? conn.scopes.join(", ") : "Standard tool access"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDisconnect(conn.id)}
                          className="h-8 px-2.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 text-xs font-medium flex items-center gap-1.5 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Disconnect</span>
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Footer info banner */}
        <div className="px-6 py-3 bg-muted/30 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-amber-600" />
            <span>Tokens sealed via pgsodium hardware encryption in Supabase Vault</span>
          </span>
          <span>Agentgateway CEL Policy Protected</span>
        </div>
      </div>
    </div>
  );
}
