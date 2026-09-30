"use client";

import React, { useState } from "react";
import { ChevronRight, Wrench, CheckCircle2, Clock } from "lucide-react";

export interface ToolExecutionTrace {
  toolName: string;
  arguments: Record<string, any>;
  result?: any;
  durationMs?: number;
  status: "success" | "failed" | "running";
}

interface ToolGroupProps {
  traces: ToolExecutionTrace[];
}

export function ToolGroup({ traces }: ToolGroupProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!traces || traces.length === 0) return null;

  const totalDuration = traces.reduce((acc, t) => acc + (t.durationMs || 0), 0);

  return (
    <div className="my-2 rounded-lg border border-zinc-200/80 bg-zinc-50/80 text-xs text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-300">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-3 py-2 text-left font-medium hover:bg-zinc-100/60 dark:hover:bg-zinc-800/40 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-2">
          <Wrench className="w-3.5 h-3.5 text-zinc-500" />
          <span>
            Used {traces.length} {traces.length === 1 ? "tool" : "tools"}
          </span>
          <span className="text-[11px] text-zinc-400 font-mono">
            ({traces.map((t) => t.toolName).join(", ")})
          </span>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-zinc-400">
          {totalDuration > 0 && (
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3" />
              {totalDuration}ms
            </span>
          )}
          <ChevronRight
            className={`w-3.5 h-3.5 transition-transform duration-200 ${
              isOpen ? "rotate-90" : ""
            }`}
          />
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-zinc-200/60 p-3 space-y-3 dark:border-zinc-800">
          {traces.map((trace, idx) => (
            <div
              key={idx}
              className="space-y-1.5 rounded border border-zinc-200/50 bg-white p-2.5 dark:border-zinc-800/60 dark:bg-zinc-950/40"
            >
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                  {trace.toolName}
                </span>
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="w-3 h-3" />
                  {trace.durationMs ? `${trace.durationMs}ms` : "Done"}
                </span>
              </div>

              {/* Arguments */}
              <div className="text-[11px]">
                <span className="text-zinc-400">Arguments: </span>
                <pre className="mt-1 overflow-x-auto rounded bg-zinc-100 p-1.5 font-mono text-[10px] text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200">
                  {JSON.stringify(trace.arguments, null, 2)}
                </pre>
              </div>

              {/* Result Preview */}
              {trace.result && (
                <div className="text-[11px]">
                  <span className="text-zinc-400">Result: </span>
                  <pre className="mt-1 max-h-32 overflow-y-auto rounded bg-zinc-100 p-1.5 font-mono text-[10px] text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200">
                    {JSON.stringify(trace.result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
