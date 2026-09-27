"use client";

import React from "react";
import { Sparkles, ArrowUpRight } from "lucide-react";

interface SuggestionCloudProps {
  onSelectPrompt: (prompt: string) => void;
  hasConnectedTools?: boolean;
}

export function SuggestionCloud({ onSelectPrompt, hasConnectedTools }: SuggestionCloudProps) {
  const smbPrompts = [
    "Compute March GST output vs input credit",
    "Fetch unpaid Zoho invoices over 30 days",
    "Search Drive for Q3 product deck",
    "Summarize recent unread Gmail threads",
  ];

  const defaultPrompts = [
    "Weather in Tokyo",
    "Show a sales dashboard",
    "Derive the geometric series",
    "Diagram a streaming chat app",
    "Add a thread list",
    "Remember my stack",
  ];

  const prompts = hasConnectedTools ? smbPrompts : defaultPrompts;

  return (
    <div className="w-full max-w-2xl mx-auto mt-6 flex flex-wrap items-center justify-center gap-2">
      {prompts.map((prompt, idx) => (
        <button
          key={idx}
          onClick={() => onSelectPrompt(prompt)}
          className="h-8 px-3 rounded-full border border-border/80 bg-white/60 dark:bg-zinc-900/60 hover:bg-accent text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors shadow-2xs group"
        >
          <span>{prompt}</span>
          <ArrowUpRight className="w-3 h-3 opacity-40 group-hover:opacity-100 transition-opacity" />
        </button>
      ))}
    </div>
  );
}
