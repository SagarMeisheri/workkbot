"use client";

import React, { useState } from "react";
import { Copy, Check, RotateCw, Flag, ChevronLeft, ChevronRight } from "lucide-react";

interface ActionBarProps {
  messageId: string;
  content: string;
  role: "user" | "assistant";
  onFlag?: () => void;
  onRegenerate?: () => void;
  branchIndex?: number;
  totalBranches?: number;
  onSelectBranch?: (index: number) => void;
}

export function ActionBar({
  messageId,
  content,
  role,
  onFlag,
  onRegenerate,
  branchIndex = 1,
  totalBranches = 1,
  onSelectBranch,
}: ActionBarProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy message:", err);
    }
  };

  return (
    <div className="flex items-center gap-1 mt-1.5 opacity-90 hover:opacity-100 transition-opacity">
      {/* Branch Selector (< 1/2 >) */}
      {totalBranches > 1 && onSelectBranch && (
        <div className="flex items-center gap-1 mr-2 px-1.5 py-0.5 rounded-md bg-muted/60 text-[11px] font-mono text-muted-foreground border border-border/40">
          <button
            onClick={() => onSelectBranch(Math.max(1, branchIndex - 1))}
            disabled={branchIndex <= 1}
            className="hover:text-foreground disabled:opacity-30"
            title="Previous branch"
          >
            <ChevronLeft className="w-3 h-3" />
          </button>
          <span>
            {branchIndex}/{totalBranches}
          </span>
          <button
            onClick={() => onSelectBranch(Math.min(totalBranches, branchIndex + 1))}
            disabled={branchIndex >= totalBranches}
            className="hover:text-foreground disabled:opacity-30"
            title="Next branch"
          >
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="h-6 w-6 rounded-md flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        title="Copy to clipboard"
      >
        {copied ? (
          <Check className="w-3 h-3 text-emerald-500" />
        ) : (
          <Copy className="w-3 h-3" />
        )}
      </button>

      {/* Regenerate button (Assistant only) */}
      {role === "assistant" && onRegenerate && (
        <button
          onClick={onRegenerate}
          className="h-6 w-6 rounded-md flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          title="Regenerate response"
        >
          <RotateCw className="w-3 h-3" />
        </button>
      )}

      {/* Flag / Report AI content button (Apple Guideline 1.2 Compliance) */}
      {role === "assistant" && onFlag && (
        <button
          onClick={onFlag}
          className="h-6 px-1.5 rounded-md flex items-center gap-1 text-[10px] text-muted-foreground hover:bg-red-500/10 hover:text-red-600 transition-colors"
          title="Flag / Report AI Content (Apple Guideline 1.2)"
        >
          <Flag className="w-3 h-3 text-muted-foreground hover:text-red-500" />
          <span className="hidden sm:inline">Report</span>
        </button>
      )}
    </div>
  );
}
