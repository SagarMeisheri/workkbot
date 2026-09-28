"use client";

import React, { useState, useEffect, useRef } from "react";
import { ActionBar } from "@/components/assistant-ui/action-bar";
import { Reasoning } from "@/components/assistant-ui/reasoning";
import { FlagModal } from "@/components/assistant-ui/flag-modal";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thought?: string;
  checkpointId?: string;
  branches?: string[];
  currentBranchIndex?: number;
}

interface AdkChatContainerProps {
  user: any;
  activeSessionId: string;
  activeConversationId?: string;
  onConsentRequired: () => void;
  children?: React.ReactNode;
}

export function useAdkStreamingChat({
  user,
  sessionId,
  conversationId,
  onConsentRequired,
}: {
  user: any;
  sessionId: string;
  conversationId?: string;
  onConsentRequired: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [flagModalState, setFlagModalState] = useState<{
    isOpen: boolean;
    messageId: string;
    content: string;
  }>({
    isOpen: false,
    messageId: "",
    content: "",
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = async (
    text: string,
    mode: "chat" | "cowork" = "chat",
    model: string = "gemini-3.8-flash",
    checkpointId?: string
  ) => {
    if (!text.trim()) return;

    const userMsgId = `msg_${Date.now()}_u`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: text,
      checkpointId,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    const assistantMsgId = `msg_${Date.now()}_a`;
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      checkpointId: userMsgId,
    };
    setMessages((prev) => [...prev, assistantMsg]);

    const token = user?.access_token || (typeof window !== "undefined" ? localStorage.getItem("workkbot_token") : null);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Model-Tier": model,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          sessionId,
          conversationId,
          model,
          checkpointId,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (response.status === 403) {
        onConsentRequired();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content:
                    "Statutory DPDP consent required before processing queries. Please accept the statutory consent notice to proceed.",
                }
              : m
          )
        );
        setIsStreaming(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No readable stream body");

      let accumulatedContent = "";
      let accumulatedThought = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value, { stream: true });
        const lines = chunkText.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.errorCode) {
                accumulatedContent += `\n\n[Error: ${data.errorMessage || "Stream interrupted"}]`;
              } else if (data.content && data.content.parts) {
                for (const part of data.content.parts) {
                  if (part.thought && part.text) {
                    accumulatedThought += part.text;
                  } else if (part.text) {
                    accumulatedContent += part.text;
                  }
                }
              }

              // Update assistant message state
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: accumulatedContent,
                        thought: accumulatedThought || undefined,
                      }
                    : m
                )
              );
            } catch (e) {
              // Ignore non-json lines like ping
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `Streaming error: ${err.message}. Ensure backend is running on port 8000.`,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
    }
  };

  const handleOpenFlagModal = (messageId: string, content: string) => {
    setFlagModalState({
      isOpen: true,
      messageId,
      content,
    });
  };

  const handleCloseFlagModal = () => {
    setFlagModalState((prev) => ({ ...prev, isOpen: false }));
  };

  return {
    messages,
    setMessages,
    isStreaming,
    sendMessage,
    flagModalState,
    handleOpenFlagModal,
    handleCloseFlagModal,
  };
}
