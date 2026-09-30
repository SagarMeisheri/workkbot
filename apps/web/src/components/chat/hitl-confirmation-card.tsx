"use client";

import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, XCircle, ArrowUpRight, Loader2 } from "lucide-react";

export interface ToolConfirmationPayload {
  tool_call_id?: string;
  toolCallId?: string;
  tool_name: string;
  provider: string;
  destination: string;
  parameters: Record<string, any>;
  risk_level?: string;
  title?: string;
  warning?: string;
}

interface HitlConfirmationCardProps {
  toolCallId: string;
  payload: ToolConfirmationPayload;
  onConfirm: (toolCallId: string, confirmed: boolean, payload?: any) => Promise<void>;
  status?: "pending" | "approved" | "declined" | "executing";
}

export const HitlConfirmationCard: React.FC<HitlConfirmationCardProps> = ({
  toolCallId,
  payload,
  onConfirm,
  status: initialStatus = "pending",
}) => {
  const [status, setStatus] = useState<"pending" | "approved" | "declined" | "executing">(initialStatus);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAction = async (confirmed: boolean) => {
    if (isSubmitting || status !== "pending") return;
    setIsSubmitting(true);
    setStatus(confirmed ? "executing" : "declined");

    try {
      await onConfirm(toolCallId, confirmed, payload.parameters);
      setStatus(confirmed ? "approved" : "declined");
    } catch (e) {
      console.error("Failed to submit tool confirmation:", e);
      setStatus("pending");
    } finally {
      setIsSubmitting(false);
    }
  };

  const formattedName = payload.tool_name
    ? payload.tool_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Action";

  return (
    <div
      data-testid="hitl-approval-card"
      className="my-3 rounded-xl border border-amber-500/30 bg-gradient-to-b from-amber-500/10 to-amber-950/20 p-4 shadow-lg backdrop-blur-md transition-all"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-amber-500/20 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-zinc-100">
              {payload.title || `Authorization Required: ${formattedName}`}
            </h4>
            <p className="text-xs text-zinc-400">
              Target: <span className="font-medium text-amber-300">{payload.destination || payload.provider}</span>
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <div>
          {status === "pending" && (
            <span className="inline-flex items-center rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-medium text-amber-300 ring-1 ring-inset ring-amber-500/40">
              Confirmation Required
            </span>
          )}
          {status === "executing" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/20 px-2.5 py-0.5 text-xs font-medium text-blue-300 ring-1 ring-inset ring-blue-500/40">
              <Loader2 className="h-3 w-3 animate-spin" /> Executing...
            </span>
          )}
          {status === "approved" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-300 ring-1 ring-inset ring-emerald-500/40">
              <CheckCircle2 className="h-3 w-3" /> Approved & Executed
            </span>
          )}
          {status === "declined" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-zinc-700/50 px-2.5 py-0.5 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-600/40">
              <XCircle className="h-3 w-3" /> Declined by User
            </span>
          )}
        </div>
      </div>

      {/* Parameter Breakdown */}
      <div className="my-3 space-y-2">
        <p className="text-xs font-medium text-zinc-400">Proposed Action Parameters:</p>
        <div className="max-h-48 overflow-y-auto rounded-lg border border-zinc-800/80 bg-zinc-950/70 p-2.5 text-xs">
          {Object.entries(payload.parameters || {}).map(([key, value]) => (
            <div key={key} className="flex flex-col py-1 sm:flex-row sm:justify-between sm:gap-2 border-b border-zinc-900 last:border-b-0">
              <span className="font-mono text-zinc-400">{key}:</span>
              <span className="break-all font-mono font-medium text-zinc-200">
                {typeof value === "object" ? JSON.stringify(value) : String(value)}
              </span>
            </div>
          ))}
          {(!payload.parameters || Object.keys(payload.parameters).length === 0) && (
            <span className="text-zinc-500 italic">No parameters specified</span>
          )}
        </div>
      </div>

      {/* Warning callout */}
      {status === "pending" && (
        <p className="mb-3 text-[11px] text-amber-300/80">
          ⚠️ {payload.warning || "Executing this action creates or alters records in your connected systems."}
        </p>
      )}

      {/* Actions */}
      {status === "pending" && (
        <div className="flex items-center justify-end gap-2 pt-1">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => handleAction(false)}
            data-testid="hitl-decline-button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800/60 px-3.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-white disabled:opacity-50"
          >
            <XCircle className="h-3.5 w-3.5" /> Decline
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => handleAction(true)}
            data-testid="hitl-confirm-button"
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-1.5 text-xs font-medium text-black transition-colors hover:bg-amber-400 disabled:opacity-50 shadow-sm"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Submitting...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-3.5 w-3.5" /> Confirm & Execute
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
