"use client";

import React, { useState } from "react";
import { Flag, X, ShieldAlert, CheckCircle } from "lucide-react";

interface FlagModalProps {
  isOpen: boolean;
  onClose: () => void;
  messageId: string;
  contentSnapshot: string;
  sessionId?: string;
  token?: string;
}

export function FlagModal({
  isOpen,
  onClose,
  messageId,
  contentSnapshot,
  sessionId,
  token,
}: FlagModalProps) {
  const [reason, setReason] = useState<string>("inaccurate");
  const [details, setDetails] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const res = await fetch("http://localhost:8000/api/v1/chat/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message_id: messageId,
          content_snapshot: contentSnapshot.slice(0, 500),
          reason,
          details,
          session_id: sessionId,
        }),
      });

      if (!res.ok) {
        throw new Error(`Report submission failed (${res.status})`);
      }

      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        onClose();
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit moderation report.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">Flag / Report AI Content</h2>
              <p className="text-xs text-muted-foreground">Apple App Store Guideline 1.2 Compliance</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {isSuccess ? (
          <div className="py-8 flex flex-col items-center justify-center text-center gap-2">
            <CheckCircle className="h-10 w-10 text-emerald-500" />
            <h3 className="text-sm font-semibold text-foreground">Report Recorded</h3>
            <p className="text-xs text-muted-foreground">
              Thank you. This incident has been logged for review and AI safety auditing.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {errorMsg && (
              <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-xs">
                {errorMsg}
              </div>
            )}

            {/* Content Preview */}
            <div className="rounded-lg bg-muted/60 p-2.5 text-xs text-muted-foreground border border-border/40">
              <span className="font-semibold block text-foreground/80 mb-1">Reported Snippet:</span>
              <p className="truncate italic">"{contentSnapshot}"</p>
            </div>

            {/* Reason selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-foreground">Reason for Report</label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full h-9 rounded-lg border border-border bg-background px-3 text-xs text-foreground outline-hidden focus:ring-1 focus:ring-primary"
              >
                <option value="inaccurate">Inaccurate / Hallucinated Information</option>
                <option value="offensive">Offensive / Harmful Language</option>
                <option value="pii_leak">Sensitive PII / Confidential Data Leak</option>
                <option value="copyright">Copyright or IP Violation</option>
                <option value="other">Other Violation</option>
              </select>
            </div>

            {/* Details input */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-foreground">Additional Context (Optional)</label>
              <textarea
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                placeholder="Describe why this response requires moderation..."
                rows={3}
                className="w-full rounded-lg border border-border bg-background p-2.5 text-xs text-foreground outline-hidden focus:ring-1 focus:ring-primary resize-none"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <button
                type="button"
                onClick={onClose}
                className="h-8 px-3 rounded-lg border border-border text-xs font-medium hover:bg-accent text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="h-8 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Flag className="h-3.5 w-3.5" />
                <span>{isSubmitting ? "Submitting..." : "Submit Report"}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
