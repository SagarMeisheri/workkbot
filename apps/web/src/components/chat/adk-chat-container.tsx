"use client";

import React, { useState, useEffect, useRef } from "react";
import { ActionBar } from "@/components/assistant-ui/action-bar";
import { Reasoning } from "@/components/assistant-ui/reasoning";
import { FlagModal } from "@/components/assistant-ui/flag-modal";
import { BACKEND_URL } from "@/lib/config";

export interface ToolTraceItem {
  toolName: string;
  provider?: string;
  arguments?: Record<string, any>;
  durationMs?: number;
  output?: any;
  status?: "success" | "failed" | "executing";
  composioLogId?: string;
}

export interface ConfirmationRequestItem {
  toolCallId: string;
  toolName: string;
  provider?: string;
  parameters: Record<string, any>;
  hint?: string;
  status?: "pending" | "executing" | "approved" | "declined";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thought?: string;
  checkpointId?: string;
  branches?: string[];
  currentBranchIndex?: number;
  confirmationRequests?: ConfirmationRequestItem[];
  toolTraces?: ToolTraceItem[];
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
    model: string = "gemini-3.8-flash",
    checkpointId?: string,
    overrideConversationId?: string,
    extraPayload?: Record<string, any>
  ) => {
    const isToolReply = Boolean(extraPayload?.type === "tool" || extraPayload?.tool_call_id);
    if (!text.trim() && !isToolReply) return;

    if (!isToolReply) {
      const userMsgId = `msg_${Date.now()}_u`;
      const userMsg: ChatMessage = {
        id: userMsgId,
        role: "user",
        content: text,
        checkpointId,
      };
      setMessages((prev) => [...prev, userMsg]);
    }

    setIsStreaming(true);

    const assistantMsgId = `msg_${Date.now()}_a`;
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      checkpointId: isToolReply ? undefined : `msg_${Date.now()}_u`,
      confirmationRequests: [],
      toolTraces: [],
    };
    setMessages((prev) => [...prev, assistantMsg]);

    const token =
      user?.access_token ||
      (typeof window !== "undefined" ? localStorage.getItem("workkbot_token") : null);

    abortControllerRef.current = new AbortController();

    try {
      const activeConvId = overrideConversationId || conversationId;
      const requestBody: Record<string, any> = {
        message: text,
        sessionId,
        conversationId: activeConvId,
        model,
        checkpointId,
        ...(extraPayload || {}),
      };

      const response = await fetch(`${BACKEND_URL}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Model-Tier": model,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(requestBody),
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
      let accumulatedConfirmations: ConfirmationRequestItem[] = [];
      let accumulatedTraces: ToolTraceItem[] = [];

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

              // Parse actions such as requested_tool_confirmations (Spec 04, R04.4)
              if (data.actions && data.actions.requested_tool_confirmations) {
                const confs = data.actions.requested_tool_confirmations;
                const newReqs: ConfirmationRequestItem[] = Object.entries(confs).map(
                  ([callId, details]: [string, any]) => ({
                    toolCallId: callId,
                    toolName: details.payload?.tool_name || "Enterprise Action",
                    provider: details.payload?.provider || "Composio Platform",
                    parameters: details.payload?.arguments || {},
                    hint: details.hint,
                    status: "pending" as const,
                  })
                );
                // Merge without duplicates
                for (const req of newReqs) {
                  if (!accumulatedConfirmations.some((c) => c.toolCallId === req.toolCallId)) {
                    accumulatedConfirmations.push(req);
                  }
                }
              }

              if (data.content && data.content.parts) {
                for (const part of data.content.parts) {
                  if (part.thought && part.text) {
                    accumulatedThought += part.text;
                  } else if (part.text) {
                    accumulatedContent += part.text;
                  } else if (part.functionCall) {
                    const fc = part.functionCall;
                    accumulatedTraces.push({
                      toolName: fc.name || "mcp_tool",
                      arguments: fc.args,
                      status: "executing",
                    });
                  } else if (part.functionResponse) {
                    const fr = part.functionResponse;
                    const existing = accumulatedTraces.find((t) => t.toolName === fr.name);
                    if (existing) {
                      existing.output = fr.response;
                      existing.status = "success";
                      if (fr.response?.composio_log_id) {
                        existing.composioLogId = fr.response.composio_log_id;
                      }
                      if (fr.response?.duration_ms) {
                        existing.durationMs = fr.response.duration_ms;
                      }
                    } else {
                      accumulatedTraces.push({
                        toolName: fr.name,
                        output: fr.response,
                        status: "success",
                        composioLogId: fr.response?.composio_log_id,
                        durationMs: fr.response?.duration_ms,
                      });
                    }
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
                        confirmationRequests: [...accumulatedConfirmations],
                        toolTraces: [...accumulatedTraces],
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

  const handleConfirmTool = async (toolCallId: string, confirmed: boolean) => {
    // 1. Immediately update UI state on the challenge
    setMessages((prev) =>
      prev.map((m) => {
        if (!m.confirmationRequests) return m;
        return {
          ...m,
          confirmationRequests: m.confirmationRequests.map((req) =>
            req.toolCallId === toolCallId
              ? { ...req, status: confirmed ? "approved" : "declined" }
              : req
          ),
        };
      })
    );

    // 2. Transmit confirmation back to backend
    await sendMessage("", undefined, undefined, undefined, {
      type: "tool",
      name: "adk_request_confirmation",
      tool_call_id: toolCallId,
      content: JSON.stringify({ confirmed, approved: confirmed }),
    });
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
    handleConfirmTool,
    flagModalState,
    handleOpenFlagModal,
    handleCloseFlagModal,
  };
}
