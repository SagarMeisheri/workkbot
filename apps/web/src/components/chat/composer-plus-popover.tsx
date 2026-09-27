"use client";

import React, { useRef, useEffect } from "react";
import {
  Paperclip,
  Camera,
  Folder,
  FileText,
  Grid,
  Palette,
  Puzzle,
  Globe,
  ChevronRight,
  Check,
} from "lucide-react";

interface ComposerPlusPopoverProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenConnectors: () => void;
  webSearchEnabled: boolean;
  onToggleWebSearch: () => void;
}

export function ComposerPlusPopover({
  isOpen,
  onClose,
  onOpenConnectors,
  webSearchEnabled,
  onToggleWebSearch,
}: ComposerPlusPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={popoverRef}
      className="absolute bottom-full left-0 mb-2 w-64 p-1.5 rounded-xl shadow-xl border border-border bg-popover text-popover-foreground z-50 animate-in fade-in slide-in-from-bottom-2 duration-150"
    >
      <div className="flex flex-col gap-0.5 text-xs">
        {/* Item 1: Files */}
        <button
          onClick={() => {
            onClose();
          }}
          className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Paperclip className="h-4 w-4 text-muted-foreground" />
            <span>Add files or photos</span>
          </div>
          <kbd className="text-[10px] text-muted-foreground font-mono bg-muted px-1.5 py-0.5 rounded">⌘U</kbd>
        </button>

        {/* Item 2: Screenshot */}
        <button
          onClick={() => {
            onClose();
          }}
          className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <Camera className="h-4 w-4 text-muted-foreground" />
          <span>Take a screenshot</span>
        </button>

        {/* Item 3: Project Binding */}
        <button
          onClick={() => {
            onClose();
          }}
          className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Folder className="h-4 w-4 text-muted-foreground" />
            <span>Add to project</span>
          </div>
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
        </button>

        {/* Item 4: Skills */}
        <button
          onClick={() => {
            onClose();
          }}
          className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span>Skills</span>
          </div>
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
        </button>

        {/* Item 5: Connectors (Spec 01) */}
        <button
          onClick={() => {
            onClose();
            onOpenConnectors();
          }}
          className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors text-foreground font-medium"
        >
          <div className="flex items-center gap-2.5">
            <Grid className="h-4 w-4 text-amber-600 dark:text-amber-500" />
            <span>Connectors</span>
          </div>
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <span>[ Yours | Discover ]</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </span>
        </button>

        {/* Item 6: Design system */}
        <button
          onClick={() => {
            onClose();
          }}
          className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Palette className="h-4 w-4 text-muted-foreground" />
            <span>Design system</span>
          </div>
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
        </button>

        {/* Item 7: Plugins */}
        <button
          onClick={() => {
            onClose();
          }}
          className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <Puzzle className="h-4 w-4 text-muted-foreground" />
          <span>Add plugins</span>
        </button>

        {/* Divider */}
        <div className="my-1 border-t border-border" />

        {/* Item 8: Web search */}
        <button
          onClick={() => {
            onToggleWebSearch();
          }}
          className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <span>Web search</span>
          </div>
          {webSearchEnabled && <Check className="h-4 w-4 text-primary" />}
        </button>
      </div>
    </div>
  );
}
