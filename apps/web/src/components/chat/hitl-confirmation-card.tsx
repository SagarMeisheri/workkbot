"use client";

import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, XCircle, Loader2, Calendar, Mail, FileText, Table, MessageSquare } from "lucide-react";

export interface ToolConfirmationPayload {
  confirmation_id: string;
  tool_name: string;
  service_name: string;
  action_title: string;
  parameters: Record<string, any>;
  security_notice?: string;
}

interface HitlConfirmationCardProps {
  confirmation: ToolConfirmationPayload;
  onConfirm: (confirmationId: string) => Promise<void> | void;
  onDecline: (confirmationId: string) => Promise<void> | void;
}

export function HitlConfirmationCard({
  confirmation,
  onConfirm,
  onDecline,
}: HitlConfirmationCardProps) {
  const [status, setStatus] = useState<"pending" | "executing" | "confirmed" | "declined">("pending");

  const getServiceIcon = () => {
    const s = confirmation.service_name.toLowerCase();
    if (s.includes("calendar")) return <Calendar className="w-5 h-5 text-blue-500" />;
    if (s.includes("gmail") || s.includes("mail")) return <Mail className="w-5 h-5 text-red-500" />;
    if (s.includes("doc")) return <FileText className="w-5 h-5 text-blue-600" />;
    if (s.includes("sheet")) return <Table className="w-5 h-5 text-emerald-500" />;
    if (s.includes("chat")) return <MessageSquare className="w-5 h-5 text-amber-500" />;
    return <ShieldAlert className="w-5 h-5 text-amber-500" />;
  };

  const handleConfirmClick = async () => {
    setStatus("executing");
    try {
      await onConfirm(confirmation.confirmation_id);
      setStatus("confirmed");
    } catch {
      setStatus("pending");
    }
  };

  const handleDeclineClick = async () => {
    setStatus("declined");
    await onDecline(confirmation.confirmation_id);
  };

  return (
    <div className="my-3 max-w-lg rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-left shadow-sm backdrop-blur-sm transition-all dark:border-amber-400/20 dark:bg-amber-950/20">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="rounded-lg bg-amber-500/10 p-2 dark:bg-amber-500/20">
            {getServiceIcon()}
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
              Action Requires Confirmation
            </span>
            <h4 className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {confirmation.action_title}
            </h4>
          </div>
        </div>

        {status === "confirmed" && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" /> Approved
          </span>
        )}
        {status === "declined" && (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-600 dark:text-rose-400">
            <XCircle className="w-3.5 h-3.5" /> Declined
          </span>
        )}
      </div>

      {/* Parameter Details */}
      <div className="mt-3 space-y-1.5 rounded-lg border border-zinc-200/60 bg-white/70 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-900/60">
        <div className="font-mono text-[11px] text-zinc-400 dark:text-zinc-500 mb-1">
          {confirmation.tool_name}
        </div>
        {Object.entries(confirmation.parameters).map(([key, val]) => (
          <div key={key} className="flex flex-col sm:flex-row sm:justify-between py-0.5 border-b border-zinc-100 dark:border-zinc-800/60 last:border-0">
            <span className="font-medium text-zinc-600 dark:text-zinc-400 capitalize">
              {key.replace(/_/g, " ")}:
            </span>
            <span className="font-mono text-zinc-900 dark:text-zinc-200 truncate max-w-[280px]">
              {typeof val === "object" ? JSON.stringify(val) : String(val)}
            </span>
          </div>
        ))}
      </div>

      {/* Security notice */}
      <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-400">
        {confirmation.security_notice || "Action requires employee authorization before execution."}
      </p>

      {/* Actions */}
      {status === "pending" && (
        <div className="mt-3.5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleDeclineClick}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 transition-colors dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Decline
          </button>
          <button
            type="button"
            onClick={handleConfirmClick}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-500 transition-colors"
          >
            Confirm & Execute
          </button>
        </div>
      )}

      {status === "executing" && (
        <div className="mt-3 flex items-center justify-end gap-2 text-xs text-zinc-500">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-500" />
          <span>Executing with Google Workspace...</span>
        </div>
      )}
    </div>
  );
}
