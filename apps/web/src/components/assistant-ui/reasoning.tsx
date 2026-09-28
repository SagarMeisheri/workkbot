"use client";

import React, { useState } from "react";
import { Sparkles, ChevronDown, ChevronRight } from "lucide-react";

interface ReasoningProps {
  text: string;
}

export function Reasoning({ text }: ReasoningProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!text) return null;

  return (
    <div className="my-2 rounded-xl border border-amber-500/20 bg-amber-500/5 overflow-hidden text-xs">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-left text-amber-700 dark:text-amber-300 font-medium hover:bg-amber-500/10 transition-colors"
      >
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Thought Process / Reasoning</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5" />
        )}
      </button>

      {isOpen && (
        <div className="px-3 py-2.5 border-t border-amber-500/15 text-muted-foreground whitespace-pre-wrap leading-relaxed text-[11px] font-mono bg-background/50">
          {text}
        </div>
      )}
    </div>
  );
}
