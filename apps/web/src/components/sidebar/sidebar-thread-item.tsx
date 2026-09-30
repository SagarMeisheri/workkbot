"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, MoreHorizontal, Pin, PinOff, Pencil, Trash2, Check, X } from "lucide-react";

export interface ThreadItemData {
  id: string;
  title: string;
  pinned?: boolean;
}

interface SidebarThreadItemProps {
  thread: ThreadItemData;
  isSelected: boolean;
  onSelect: (thread: ThreadItemData) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newTitle: string) => void;
  onPin: (id: string, pinned: boolean) => void;
}

export function SidebarThreadItem({
  thread,
  isSelected,
  onSelect,
  onDelete,
  onRename,
  onPin,
}: SidebarThreadItemProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(thread.title);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync edit title if thread title changes externally
  useEffect(() => {
    setEditTitle(thread.title);
  }, [thread.title]);

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  // Click outside to close menu
  useEffect(() => {
    if (!isMenuOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setIsMenuOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMenuOpen]);

  const handleSaveRename = () => {
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== thread.title) {
      onRename(thread.id, trimmed);
    } else {
      setEditTitle(thread.title);
    }
    setIsEditing(false);
  };

  const handleCancelRename = () => {
    setEditTitle(thread.title);
    setIsEditing(false);
  };

  return (
    <div className="relative group">
      {isEditing ? (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-accent/80 border border-primary/40 shadow-xs">
          <MessageSquare className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSaveRename();
              if (e.key === "Escape") handleCancelRename();
            }}
            className="flex-1 bg-transparent text-xs font-medium text-foreground focus:outline-hidden py-0.5 truncate"
          />
          <button
            onClick={handleSaveRename}
            className="p-1 hover:bg-background/80 rounded-md text-primary transition-colors"
            title="Save"
          >
            <Check className="w-3 h-3" />
          </button>
          <button
            onClick={handleCancelRename}
            className="p-1 hover:bg-background/80 rounded-md text-muted-foreground transition-colors"
            title="Cancel"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ) : (
        <div
          onClick={() => onSelect(thread)}
          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-all cursor-pointer flex items-center justify-between gap-1.5 ${
            isSelected
              ? "bg-accent/90 text-accent-foreground font-semibold shadow-2xs border border-border/70"
              : "hover:bg-accent/50 text-foreground/80 hover:text-foreground"
          }`}
        >
          <div className="flex items-center gap-2 truncate flex-1 min-w-0">
            {thread.pinned ? (
              <Pin className="w-3.5 h-3.5 text-amber-500 fill-amber-500/20 shrink-0" />
            ) : (
              <MessageSquare
                className={`w-3.5 h-3.5 shrink-0 ${
                  isSelected ? "text-primary" : "text-muted-foreground"
                }`}
              />
            )}
            <span className="truncate">{thread.title}</span>
          </div>

          {/* Three-dots menu trigger */}
          <button
            ref={buttonRef}
            onClick={(e) => {
              e.stopPropagation();
              setIsMenuOpen((prev) => !prev);
            }}
            aria-label="Thread actions"
            className={`p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-background/80 transition-opacity shrink-0 ${
              isMenuOpen ? "opacity-100 bg-background/80" : "opacity-0 group-hover:opacity-100"
            }`}
          >
            <MoreHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Popover / Dropdown Menu: strictly 3 options (Pin, Rename, Delete) */}
      {isMenuOpen && (
        <div
          ref={menuRef}
          className="absolute right-0 top-full mt-1 w-36 rounded-xl border border-border bg-popover/95 backdrop-blur-md shadow-lg p-1 z-50 animate-in fade-in zoom-in-95 duration-100 flex flex-col gap-0.5 text-xs"
        >
          {/* 1. Pin / Unpin */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsMenuOpen(false);
              onPin(thread.id, !thread.pinned);
            }}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-foreground hover:bg-accent hover:text-accent-foreground transition-colors text-left"
          >
            {thread.pinned ? (
              <>
                <PinOff className="w-3.5 h-3.5 text-muted-foreground" />
                <span>Unpin</span>
              </>
            ) : (
              <>
                <Pin className="w-3.5 h-3.5 text-muted-foreground" />
                <span>Pin</span>
              </>
            )}
          </button>

          {/* 2. Rename */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsMenuOpen(false);
              setIsEditing(true);
            }}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-foreground hover:bg-accent hover:text-accent-foreground transition-colors text-left"
          >
            <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Rename</span>
          </button>

          {/* 3. Delete (Destructive) */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsMenuOpen(false);
              onDelete(thread.id);
            }}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-destructive hover:bg-destructive/10 dark:hover:bg-destructive/20 font-medium transition-colors text-left"
          >
            <Trash2 className="w-3.5 h-3.5 text-destructive" />
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );
}
