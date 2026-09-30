"use client";

import React, { useState } from "react";
import { ShieldAlert, Check, X, Loader2, ArrowRight } from "lucide-react";

export interface HitlConfirmationCardProps {
  toolCallId: string;
  toolName: string;
  provider?: string;
  parameters: Record<string, any>;
  hint?: string;
  securityNotice?: string;
  onConfirm: (toolCallId: string, confirmed: boolean) => Promise<void> | void;
  status?: "pending" | "executing" | "approved" | "declined";
}

export function HitlConfirmationCard({
  toolCallId,
  toolName,
  provider = "Enterprise Connector",
  parameters,
  hint = "Authorization required for mutating action",
  securityNotice = "This action will modify external enterprise state.",
  onConfirm,
  status: initialStatus = "pending",
}: HitlConfirmationCardProps) {
  const [status, setStatus] = useState<"pending" | "executing" | "approved" | "declined">(
    initialStatus
  );

  const handleAction = async (confirmed: boolean) => {
    setStatus("executing");
    try {
      await onConfirm(toolCallId, confirmed);
      setStatus(confirmed ? "approved" : "declined");
    } catch (e) {
      console.error("Confirmation error:", e);
      setStatus("pending");
    }
  };

  return (
    <div
      data-testid="hitl-confirmation-card"
      className="my-3 max-w-xl rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 shadow-lg backdrop-blur-md transition-all duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-amber-500/20 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Authorization Required
            </h4>
            <p className="text-xs text-neutral-400">{hint}</p>
          </div>
        </div>

        {/* Status Badge */}
        {status === "approved" && (
          <span className="flex items-center gap-1 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
            <Check className="h-3 w-3" /> Approved
          </span>
        )}
        {status === "declined" && (
          <span className="flex items-center gap-1 rounded-full bg-red-500/20 px-2.5 py-0.5 text-xs font-medium text-red-400">
            <X className="h-3 w-3" /> Declined
          </span>
        )}
        {status === "executing" && (
          <span className="flex items-center gap-1 rounded-full bg-blue-500/20 px-2.5 py-0.5 text-xs font-medium text-blue-400">
            <Loader2 className="h-3 w-3 animate-spin" /> Executing...
          </span>
        )}
      </div>

      {/* Target Tool Details */}
      <div className="mt-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-neutral-400">Action:</span>
          <span
            data-testid="tool-name-badge"
            className="rounded bg-neutral-800 px-2 py-0.5 font-mono text-xs font-semibold text-neutral-200"
          >
            {toolName}
          </span>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-neutral-400">Destination Provider:</span>
          <span className="text-xs font-medium text-neutral-300">{provider}</span>
        </div>

        {/* Parameter Breakdown */}
        {parameters && Object.keys(parameters).length > 0 && (
          <div className="mt-2 rounded-lg bg-neutral-900/80 p-2.5 text-xs">
            <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-neutral-400">
              Parameters:
            </div>
            <div className="space-y-1 font-mono text-xs text-neutral-300">
              {Object.entries(parameters).map(([key, val]) => (
                <div key={key} className="flex justify-between gap-4">
                  <span className="text-neutral-400">{key}:</span>
                  <span className="truncate text-right font-medium text-neutral-200">
                    {typeof val === "object" ? JSON.stringify(val) : String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Security Notice */}
        <p className="text-[11px] italic text-neutral-400">{securityNotice}</p>
      </div>

      {/* Action Buttons */}
      {status === "pending" && (
        <div className="mt-3.5 flex items-center justify-end gap-2 pt-1">
          <button
            type="button"
            data-testid="hitl-decline-button"
            onClick={() => handleAction(false)}
            className="flex items-center gap-1 rounded-lg border border-neutral-700 bg-neutral-800/80 px-3 py-1.5 text-xs font-medium text-neutral-300 transition-colors hover:bg-neutral-700 hover:text-white"
          >
            <X className="h-3.5 w-3.5" /> Decline
          </button>
          <button
            type="button"
            data-testid="hitl-confirm-button"
            onClick={() => handleAction(true)}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:bg-emerald-500"
          >
            <Check className="h-3.5 w-3.5" /> Confirm & Execute
          </button>
        </div>
      )}
    </div>
  );
}
