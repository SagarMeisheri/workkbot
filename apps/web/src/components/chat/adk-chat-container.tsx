"use client";

import React, { useState, useEffect, useRef } from "react";
import { ActionBar } from "@/components/assistant-ui/action-bar";
import { Reasoning } from "@/components/assistant-ui/reasoning";
import { FlagModal } from "@/components/assistant-ui/flag-modal";
import { BACKEND_URL } from "@/lib/config";
import { ToolConfirmationPayload } from "./hitl-confirmation-card";
import { ToolExecutionTrace } from "../assistant-ui/elements/tool-group.aui";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thought?: string;
  checkpointId?: string;
  branches?: string[];
  currentBranchIndex?: number;
  toolConfirmations?: ToolConfirmationPayload[];
  toolTraces?: ToolExecutionTrace[];
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

  const processSseStream = async (
    response: Response,
    targetMsgId: string,
    initialContent: string = "",
    initialThought: string = "",
    initialConfirmations: ToolConfirmationPayload[] = [],
    initialTraces: ToolExecutionTrace[] = []
  ) => {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) throw new Error("No readable stream body");

    let accumulatedContent = initialContent;
    let accumulatedThought = initialThought;
    const accumulatedConfirmations = [...initialConfirmations];
    const accumulatedTraces = [...initialTraces];

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
            }

            // 1. In-Chat HITL Tool Confirmation Requests
            if (data.type === "tool_confirmation_request" && data.toolCallId) {
              const existingIdx = accumulatedConfirmations.findIndex(
                (c) => (c.toolCallId || c.tool_call_id) === data.toolCallId
              );
              const confPayload: ToolConfirmationPayload = {
                toolCallId: data.toolCallId,
                tool_call_id: data.toolCallId,
                tool_name: data.payload?.tool_name || data.toolName || "External Action",
                provider: data.payload?.provider || "custom",
                destination: data.payload?.destination || "External Integration",
                parameters: data.payload?.parameters || {},
                title: data.payload?.title,
                warning: data.payload?.warning,
              };

              if (existingIdx >= 0) {
                accumulatedConfirmations[existingIdx] = confPayload;
              } else {
                accumulatedConfirmations.push(confPayload);
              }
            }

            // 2. Tool Execution Traces
            if (data.type === "tool_call" && data.toolName) {
              accumulatedTraces.push({
                toolName: data.toolName,
                arguments: data.arguments || {},
              });
            }

            // 3. Regular model text and reasoning parts
            if (data.content && data.content.parts) {
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
                m.id === targetMsgId
                  ? {
                      ...m,
                      content: accumulatedContent,
                      thought: accumulatedThought || undefined,
                      toolConfirmations: accumulatedConfirmations.length > 0 ? accumulatedConfirmations : undefined,
                      toolTraces: accumulatedTraces.length > 0 ? accumulatedTraces : undefined,
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
  };

  const sendMessage = async (
    text: string,
    model: string = "gemini-3.8-flash",
    checkpointId?: string,
    overrideConversationId?: string
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
      const activeConvId = overrideConversationId || conversationId;
      const response = await fetch(`${BACKEND_URL}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Model-Tier": model,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          sessionId,
          conversationId: activeConvId,
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

      await processSseStream(response, assistantMsgId);
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

  const confirmTool = async (
    toolCallId: string,
    confirmed: boolean,
    payload?: any
  ) => {
    setIsStreaming(true);
    const token = user?.access_token || (typeof window !== "undefined" ? localStorage.getItem("workkbot_token") : null);

    // Target the most recent assistant message with this tool confirmation
    const targetMsg = messages
      .slice()
      .reverse()
      .find((m) =>
        m.toolConfirmations?.some((c) => (c.toolCallId || c.tool_call_id) === toolCallId)
      );

    const targetMsgId = targetMsg ? targetMsg.id : `msg_${Date.now()}_a`;

    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          sessionId,
          conversationId,
          toolConfirmation: {
            toolCallId,
            confirmed,
            payload,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      await processSseStream(
        response,
        targetMsgId,
        targetMsg?.content || "",
        targetMsg?.thought || "",
        targetMsg?.toolConfirmations || [],
        targetMsg?.toolTraces || []
      );
    } catch (err: any) {
      console.error("Error during tool confirmation execution:", err);
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
    confirmTool,
    flagModalState,
    handleOpenFlagModal,
    handleCloseFlagModal,
  };
}
