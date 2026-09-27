"use client";

import React, { useState, useEffect } from "react";
import { Plus, MessageSquare, ExternalLink, Shield } from "lucide-react";
import { SidebarAuthFooter } from "@/components/sidebar/sidebar-auth-footer";
import { ThreadHeader } from "@/components/chat/thread-header";
import { ChatHeroGreeting } from "@/components/chat/chat-hero-greeting";
import { FloatingComposer } from "@/components/chat/floating-composer";
import { SuggestionCloud } from "@/components/chat/suggestion-cloud";
import { ConnectorsHubModal } from "@/components/chat/connectors-hub-modal";
import { ConsentModal } from "@/components/auth/consent-modal";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function WorkspacePage() {
  const [user, setUser] = useState<any>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isCanvasOpen, setIsCanvasOpen] = useState(false);
  const [isConnectorsOpen, setIsConnectorsOpen] = useState(false);
  const [isConsentOpen, setIsConsentOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [threads, setThreads] = useState<string[]>([
    "GST Calculation March",
    "Zoho Books Ledger Sync",
    "Google Drive Q3 Architecture",
  ]);
  const [activeThread, setActiveThread] = useState<string>("New chat");

  useEffect(() => {
    // Check local auth state
    const authData = localStorage.getItem("workkbot_auth");
    if (authData) {
      try {
        const parsed = JSON.parse(authData);
        setUser(parsed);
        // Check if user has consented
        const consented = localStorage.getItem("workkbot_consented");
        if (!consented) {
          setIsConsentOpen(true);
        }
      } catch (e) {
        console.error("Auth parsing error:", e);
      }
    }
  }, []);

  const handleSendMessage = (text: string, mode: "chat" | "cowork", model: string) => {
    const userMsg: Message = {
      id: `msg_${Date.now()}_u`,
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setActiveThread(text.slice(0, 30));

    // Simulate response with tool grounding simulation
    setTimeout(() => {
      let reply = `Processed via ${model} in ${mode} mode.`;
      if (text.toLowerCase().includes("gst")) {
        reply = "Here is the summary of your March GST computation: Total Output IGST: ₹1,42,800. Net Input Tax Credit claimed: ₹94,200. Balance payable before April 20th: ₹48,600.";
      } else if (text.toLowerCase().includes("zoho")) {
        reply = "Retrieved 3 unpaid invoices from Zoho Books (.in datacenter) totaling ₹2,15,400 with overdue ageing > 30 days.";
      }
      const assistantMsg: Message = {
        id: `msg_${Date.now()}_a`,
        role: "assistant",
        content: reply,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    }, 600);
  };

  const handleNewThread = () => {
    setMessages([]);
    setActiveThread("New chat");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* 1. Collapsible Left Sidebar */}
      <aside
        className={`border-r border-sidebar-border bg-sidebar flex flex-col justify-between shrink-0 transition-all duration-300 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-0 overflow-hidden"
        }`}
      >
        <div className="flex flex-col h-full overflow-hidden">
          {/* Sidebar Header */}
          <div className="h-14 px-4 flex items-center justify-between border-b border-sidebar-border shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-amber-600 dark:text-amber-500 text-lg font-serif">✳</span>
              <span className="font-semibold text-sm tracking-tight text-foreground">Workkbot</span>
            </div>
          </div>

          {/* New Thread Action Pill */}
          <div className="p-3">
            <button
              onClick={handleNewThread}
              className="w-full h-9 rounded-full border border-border bg-card hover:bg-accent text-foreground px-4 text-xs font-medium flex items-center gap-2 transition-colors shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New thread</span>
            </button>
          </div>

          {/* Thread History Items */}
          <div className="flex-1 overflow-y-auto px-3 py-2 flex flex-col gap-4">
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-2">
                Today
              </span>
              <div className="mt-1 flex flex-col gap-0.5">
                {threads.slice(0, 2).map((t, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActiveThread(t)}
                    className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-accent text-foreground/90 truncate transition-colors flex items-center gap-2"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    <span className="truncate">{t}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-2">
                Previous 7 Days
              </span>
              <div className="mt-1 flex flex-col gap-0.5">
                {threads.slice(2).map((t, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActiveThread(t)}
                    className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-accent text-foreground/90 truncate transition-colors flex items-center gap-2"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    <span className="truncate">{t}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Auth Footer (State 1: -> Sign in vs State 2: Avatar & Settings) */}
        <SidebarAuthFooter
          user={user}
          onOpenConnectors={() => setIsConnectorsOpen(true)}
          onOpenConsentModal={() => setIsConsentOpen(true)}
        />
      </aside>

      {/* 2. Main Stage */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-background">
        {/* Top Header */}
        <ThreadHeader
          title={activeThread}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          isCanvasOpen={isCanvasOpen}
          onToggleCanvas={() => setIsCanvasOpen(!isCanvasOpen)}
        />

        {/* Viewport: Main Chat + Optional Canvas Split */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Stream Viewport */}
          <div className={`flex-1 flex flex-col overflow-y-auto px-4 py-6 transition-all ${isCanvasOpen ? "w-1/2" : "w-full"}`}>
            {messages.length === 0 ? (
              /* Empty Cold Landing State */
              <div className="flex-1 flex flex-col items-center justify-center my-auto">
                <ChatHeroGreeting user={user} />
                <FloatingComposer
                  onSendMessage={handleSendMessage}
                  onOpenConnectors={() => setIsConnectorsOpen(true)}
                />
                <SuggestionCloud
                  onSelectPrompt={(p) => handleSendMessage(p, "chat", "gemini-2.0-flash")}
                  hasConnectedTools={Boolean(user)}
                />
              </div>
            ) : (
              /* Active Message Stream */
              <div className="w-full max-w-2xl mx-auto flex flex-col gap-6 pb-24">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-xs"
                          : "bg-muted/70 text-foreground border border-border/60 rounded-bl-xs shadow-2xs"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Anchored Bottom Composer during conversation */}
            {messages.length > 0 && (
              <div className="sticky bottom-4 w-full pt-2">
                <FloatingComposer
                  onSendMessage={handleSendMessage}
                  onOpenConnectors={() => setIsConnectorsOpen(true)}
                />
              </div>
            )}
          </div>

          {/* Optional Split Canvas Artifact Frame */}
          {isCanvasOpen && (
            <div className="w-1/2 border-l border-border bg-card p-6 flex flex-col">
              <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Artifact Canvas
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 text-[10px] font-medium">
                    Sandboxed
                  </span>
                </div>
              </div>
              <div className="flex-1 flex items-center justify-center border border-dashed border-border rounded-xl text-xs text-muted-foreground">
                No active artifact open in canvas. Toggle artifacts from chat responses.
              </div>
            </div>
          )}
        </div>
      </main>

      {/* 3. Connectors Hub Modal [ Yours | Discover ] */}
      <ConnectorsHubModal
        isOpen={isConnectorsOpen}
        onClose={() => setIsConnectorsOpen(false)}
        user={user}
      />

      {/* 4. DPDP Act 2023 Statutory Consent Modal */}
      <ConsentModal
        isOpen={isConsentOpen}
        onConsentSuccess={() => setIsConsentOpen(false)}
        user={user}
      />
    </div>
  );
}
