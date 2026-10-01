"use client";

import React, { useState, useRef, useEffect } from "react";
import { Sparkles, Check, Layers } from "lucide-react";

export interface QuickSkillsPopoverProps {
  isOpen: boolean;
  onClose: () => void;
  alignDirection?: "up" | "down";
}

interface SkillItem {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

const DEFAULT_SKILLS: SkillItem[] = [
  {
    id: "gst_billing",
    name: "GST Invoicing & E-Way Bills",
    description: "Calculates CGST/SGST/IGST and audits B2B invoices.",
    enabled: true,
  },
  {
    id: "financial_audit",
    name: "Financial Statement Auditor",
    description: "Inspects Balance Sheets, P&L statements, and reconciliation.",
    enabled: true,
  },
  {
    id: "meeting_transcripts",
    name: "Meeting Action Items",
    description: "Extracts key decisions and timelines from transcripts.",
    enabled: true,
  },
  {
    id: "contract_analyst",
    name: "Contract & Agreement Review",
    description: "Detects liability caps, indemnities, and termination clauses.",
    enabled: false,
  },
];

export function QuickSkillsPopover({
  isOpen,
  onClose,
  alignDirection = "down",
}: QuickSkillsPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [skills, setSkills] = useState<SkillItem[]>(DEFAULT_SKILLS);

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

  const toggleSkill = (id: string) => {
    setSkills((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const enabledCount = skills.filter((s) => s.enabled).length;

  return (
    <div
      ref={popoverRef}
      className={`absolute ${
        alignDirection === "up" ? "bottom-full mb-2" : "top-full mt-2"
      } left-0 w-72 rounded-2xl border border-border bg-popover text-popover-foreground shadow-2xl z-50 overflow-hidden animate-in fade-in ${
        alignDirection === "up" ? "slide-in-from-bottom-2" : "slide-in-from-top-2"
      } duration-150`}
    >
      {/* Header */}
      <div className="px-3.5 py-2.5 border-b border-border/80 flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
          <span className="text-xs font-semibold text-foreground">Skills</span>
          <span className="px-1.5 py-0.5 rounded-full bg-accent text-[10px] font-medium text-foreground">
            {enabledCount} active
          </span>
        </div>
      </div>

      {/* Skills list */}
      <div className="p-1.5 flex flex-col gap-1 max-h-64 overflow-y-auto">
        {skills.map((skill) => (
          <div
            key={skill.id}
            onClick={() => toggleSkill(skill.id)}
            className="flex items-center justify-between px-2.5 py-2 rounded-xl hover:bg-accent/60 cursor-pointer transition-colors"
          >
            <div className="flex flex-col min-w-0 pr-2">
              <span className="text-xs font-medium text-foreground truncate">{skill.name}</span>
              <span className="text-[10px] text-muted-foreground truncate">{skill.description}</span>
            </div>

            {/* Toggle Switch */}
            <button
              type="button"
              role="switch"
              aria-checked={skill.enabled}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                skill.enabled ? "bg-amber-600 dark:bg-amber-500" : "bg-zinc-300 dark:bg-zinc-700"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                  skill.enabled ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
