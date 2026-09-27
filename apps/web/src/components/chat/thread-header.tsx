"use client";

import React from "react";
import { MoreHorizontal, ExternalLink, PanelLeft, Share2, Sparkles } from "lucide-react";

interface ThreadHeaderProps {
  title?: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isCanvasOpen: boolean;
  onToggleCanvas: () => void;
}

export function ThreadHeader({
  title = "New chat",
  isSidebarOpen,
  onToggleSidebar,
  isCanvasOpen,
  onToggleCanvas,
}: ThreadHeaderProps) {
  return (
    <header className="h-14 border-b border-border/60 px-4 flex items-center justify-between bg-background shrink-0">
      {/* Left: Sidebar toggle + Thread title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="h-8 w-8 rounded-lg hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        >
          <PanelLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-medium text-foreground truncate max-w-xs sm:max-w-md">
          {title}
        </span>
      </div>

      {/* Right: Actions and Canvas split toggle */}
      <div className="flex items-center gap-1.5">
        <button
          className="h-8 w-8 rounded-lg hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          title="Share thread"
        >
          <Share2 className="h-4 w-4" />
        </button>

        <button
          className="h-8 w-8 rounded-lg hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          title="Options"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>

        <div className="w-px h-4 bg-border mx-1" />

        {/* Canvas Split Toggle [↗] */}
        <button
          onClick={onToggleCanvas}
          className={`h-8 px-2.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition-colors ${
            isCanvasOpen
              ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300"
              : "border-border hover:bg-accent text-muted-foreground hover:text-foreground"
          }`}
          title="Toggle Canvas artifact split pane"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Canvas</span>
        </button>
      </div>
    </header>
  );
}
