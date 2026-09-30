"use client";

import React, { useState, useEffect, useRef } from "react";
import { Plus, MessageSquare, ExternalLink, Shield, ArrowDown } from "lucide-react";
import { SidebarAuthFooter } from "@/components/sidebar/sidebar-auth-footer";
import { ThreadHeader } from "@/components/chat/thread-header";
import { ChatHeroGreeting } from "@/components/chat/chat-hero-greeting";
import { FloatingComposer } from "@/components/chat/floating-composer";
import { SuggestionCloud } from "@/components/chat/suggestion-cloud";
import { ConnectorsHubModal } from "@/components/chat/connectors-hub-modal";
import { ConsentModal } from "@/components/auth/consent-modal";
import { useAdkStreamingChat, type ChatMessage } from "@/components/chat/adk-chat-container";
import { Reasoning } from "@/components/assistant-ui/reasoning";
import { ActionBar } from "@/components/assistant-ui/action-bar";
import { FlagModal } from "@/components/assistant-ui/flag-modal";
import { MarkdownContent } from "@/components/chat/markdown-content";
import { supabase } from "@/lib/supabase";
import { BACKEND_URL } from "@/lib/config";

export default function WorkspacePage() {
  const [user, setUser] = useState<any>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isCanvasOpen, setIsCanvasOpen] = useState(false);
  const [isConnectorsOpen, setIsConnectorsOpen] = useState(false);
  const [isConsentOpen, setIsConsentOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => `sess_${Date.now()}`);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [threads, setThreads] = useState<Array<{ id: string; title: string }>>([]);
  const [activeThread, setActiveThread] = useState<string>("New chat");
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setShowScrollBottom(distanceFromBottom > 100);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const {
    messages,
    setMessages,
    isStreaming,
    sendMessage,
    flagModalState,
    handleOpenFlagModal,
    handleCloseFlagModal,
  } = useAdkStreamingChat({
    user,
    sessionId,
    conversationId,
    onConsentRequired: () => setIsConsentOpen(true),
  });

  // Auto-scroll to bottom of conversation during streaming or when new messages arrive
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming]);

  const fetchConversations = async (token: string) => {
    try {
      const convRes = await fetch(`${BACKEND_URL}/api/v1/conversations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (convRes.ok) {
        const data = await convRes.json();
        if (data.conversations && Array.isArray(data.conversations)) {
          setThreads(data.conversations.map((c: any) => ({ id: c.id, title: c.title || "New chat" })));
        }
      }
    } catch (e) {
      console.error("Fetch conversations error:", e);
    }
  };

  useEffect(() => {
    // 1. Check live Supabase Session
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("*, organizations(*)")
          .eq("id", session.user.id)
          .maybeSingle();

        const p = profile as any;
        const userObj = {
          user_id: session.user.id,
          email: session.user.email,
          first_name: p?.first_name || session.user.user_metadata?.first_name || "Employee",
          org_id: p?.org_id || session.user.app_metadata?.org_id,
          org_name: p?.organizations?.name || "Workkbot SMB India",
          role: p?.role || "member",
          avatar_url: p?.avatar_url || session.user.user_metadata?.avatar_url,
          access_token: session.access_token,
        };
        setUser(userObj);

        // Check live consent status from backend
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/consent/status`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          });
          if (res.ok) {
            const consentData = await res.json();
            if (!consentData.has_consented) {
              setIsConsentOpen(true);
            }
          }
        } catch (e) {
          console.error("Consent check error:", e);
        }

        // Fetch user conversations from Supabase
        await fetchConversations(session.access_token);
      } else {
        // Fallback to local storage (for reviewer mode or cached tokens)
        const authData = localStorage.getItem("workkbot_auth");
        const token = localStorage.getItem("workkbot_token");
        if (authData) {
          try {
            const parsed = JSON.parse(authData);
            if (token) parsed.access_token = token;
            setUser(parsed);
            const consented = localStorage.getItem("workkbot_consented");
            if (!consented) {
              setIsConsentOpen(true);
            }
            if (token) {
              await fetchConversations(token);
            }
          } catch (e) {
            console.error("Auth parsing error:", e);
          }
        }
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("*, organizations(*)")
          .eq("id", session.user.id)
          .maybeSingle();

        const p = profile as any;
        setUser({
          user_id: session.user.id,
          email: session.user.email,
          first_name: p?.first_name || session.user.user_metadata?.first_name || "Employee",
          org_id: p?.org_id || session.user.app_metadata?.org_id,
          org_name: p?.organizations?.name || "Workkbot SMB India",
          role: p?.role || "member",
          avatar_url: p?.avatar_url || session.user.user_metadata?.avatar_url,
          access_token: session.access_token,
        });
      } else if (event === "SIGNED_OUT") {
        setUser(null);
        localStorage.removeItem("workkbot_auth");
        localStorage.removeItem("workkbot_token");
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleSelectThread = async (t: { id: string; title: string }) => {
    setActiveThread(t.title);
    setConversationId(t.id);
    setSessionId(`sess_${t.id}`);

    const token = user?.access_token || (typeof window !== "undefined" ? localStorage.getItem("workkbot_token") : null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/conversations/${t.id}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        const loadedMessages: ChatMessage[] = [];
        if (data.events && Array.isArray(data.events)) {
          for (const ev of data.events) {
            let text = "";
            let thought = "";
            const content = ev.content;
            if (content && typeof content === "object" && Array.isArray(content.parts)) {
              for (const part of content.parts) {
                if (part.thought) {
                  thought += (part.text || "");
                } else if (part.text) {
                  text += part.text;
                }
              }
            } else if (typeof content === "string") {
              text = content;
            } else if (content && typeof content === "object" && content.text) {
              text = content.text;
            }
            if (text || thought) {
              loadedMessages.push({
                id: ev.id,
                role: ev.author === "user" ? "user" : "assistant",
                content: text,
                thought: thought || undefined,
                checkpointId: ev.parent_event_id,
              });
            }
          }
        }
        setMessages(loadedMessages);
      }
    } catch (e) {
      console.error("Failed to load conversation events from Supabase:", e);
    }
  };

  const handleSendMessage = async (text: string, mode: "chat" | "cowork", model: string) => {
    const threadTitle = text.slice(0, 35);
    let activeConvId = conversationId;

    if (!activeConvId || activeThread === "New chat") {
      activeConvId = crypto.randomUUID();
      setActiveThread(threadTitle);
      setConversationId(activeConvId);
      setThreads((prev) => [{ id: activeConvId!, title: threadTitle }, ...prev.filter(t => t.id !== activeConvId)]);

      // Persist conversation directly in Supabase
      const token = user?.access_token || (typeof window !== "undefined" ? localStorage.getItem("workkbot_token") : null);
      if (token) {
        fetch(`${BACKEND_URL}/api/v1/conversations`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            id: activeConvId,
            title: threadTitle,
          }),
        }).catch((err) => console.error("Error creating conversation in Supabase:", err));
      }
    }

    await sendMessage(text, mode, model, undefined, activeConvId);
  };

  const handleNewThread = () => {
    setMessages([]);
    setSessionId(`sess_${Date.now()}`);
    setConversationId(undefined);
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
            {threads.length === 0 ? (
              <div className="px-3 py-6 text-center text-xs text-muted-foreground/70">
                No recent conversations
              </div>
            ) : (
              <div>
                <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-2">
                  Recent Threads
                </span>
                <div className="mt-1 flex flex-col gap-0.5">
                  {threads.map((t, idx) => (
                    <button
                      key={t.id || idx}
                      onClick={() => handleSelectThread(t)}
                      className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs truncate transition-colors flex items-center gap-2 ${
                        activeThread === t.title
                          ? "bg-accent text-accent-foreground font-medium"
                          : "hover:bg-accent/60 text-foreground/80"
                      }`}
                    >
                      <MessageSquare className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      <span className="truncate">{t.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
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
          <div className={`flex-1 flex flex-col h-full overflow-hidden transition-all ${isCanvasOpen ? "w-1/2" : "w-full"}`}>
            {messages.length === 0 ? (
              /* Empty Cold Landing State */
              <div className="flex-1 flex flex-col items-center justify-center overflow-y-auto px-4 py-6 my-auto">
                <ChatHeroGreeting user={user} />
                <FloatingComposer
                  onSendMessage={handleSendMessage}
                  onOpenConnectors={() => setIsConnectorsOpen(true)}
                />
                <SuggestionCloud
                  onSelectPrompt={(p) => handleSendMessage(p, "chat", "gemini-3.8-flash")}
                  hasConnectedTools={Boolean(user)}
                />
              </div>
            ) : (
              /* Active Conversation Mode */
              <div className="flex-1 flex flex-col min-h-0 relative">
                {/* Scrollable Message Stream: Text stays strictly above the composer dock */}
                <div
                  ref={scrollContainerRef}
                  onScroll={handleScroll}
                  className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth"
                >
                  <div className="w-full max-w-3xl mx-auto flex flex-col gap-6 pb-6">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${
                          msg.role === "user" ? "items-end" : "items-start"
                        }`}
                      >
                        {/* Gemini Reasoning / Thoughts */}
                        {msg.role === "assistant" && msg.thought && (
                          <Reasoning text={msg.thought} />
                        )}

                        <div
                          className={`p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground rounded-br-xs whitespace-pre-wrap"
                              : "bg-muted/70 text-foreground border border-border/60 rounded-bl-xs shadow-2xs"
                          }`}
                        >
                          {msg.role === "assistant" ? (
                            msg.content ? (
                              <MarkdownContent content={msg.content} />
                            ) : isStreaming ? (
                              <span className="text-muted-foreground animate-pulse">Thinking...</span>
                            ) : null
                          ) : (
                            msg.content
                          )}
                        </div>

                        {/* Action Bar with Apple 1.2 Moderation Flag & Regenerate */}
                        {msg.content && (
                          <ActionBar
                            messageId={msg.id}
                            content={msg.content}
                            role={msg.role}
                            onFlag={
                              msg.role === "assistant"
                                ? () => handleOpenFlagModal(msg.id, msg.content)
                                : undefined
                            }
                            onRegenerate={
                              msg.role === "assistant"
                                ? () => sendMessage("Regenerate response with additional details", "chat", "gemini-3.8-flash", msg.checkpointId)
                                : undefined
                            }
                          />
                        )}
                      </div>
                    ))}
                    {/* Auto-scroll target anchor */}
                    <div ref={messagesEndRef} />
                  </div>
                </div>

                {/* Docked Bottom Composer: Compact single-row pill when conversation is active */}
                <div className="relative w-full shrink-0 px-4 pb-4 pt-1 bg-gradient-to-t from-background via-background/95 to-transparent">
                  {/* Floating Scroll-to-Bottom Arrow Button (like Claude) */}
                  {showScrollBottom && (
                    <div className="absolute -top-10 left-1/2 -translate-x-1/2 z-20 animate-in fade-in zoom-in-90 duration-150">
                      <button
                        onClick={scrollToBottom}
                        className="h-8 w-8 rounded-full border border-border bg-background shadow-md flex items-center justify-center text-muted-foreground hover:text-foreground transition-all hover:scale-105"
                        title="Scroll to latest response"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                    </div>
                  )}

                  <FloatingComposer
                    compact={true}
                    onSendMessage={handleSendMessage}
                    onOpenConnectors={() => setIsConnectorsOpen(true)}
                  />
                </div>
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

      {/* 5. Apple App Store Guideline 1.2 Content Flag Modal */}
      <FlagModal
        isOpen={flagModalState.isOpen}
        onClose={handleCloseFlagModal}
        messageId={flagModalState.messageId}
        contentSnapshot={flagModalState.content}
        sessionId={sessionId}
        token={user?.access_token}
      />
    </div>
  );
}
