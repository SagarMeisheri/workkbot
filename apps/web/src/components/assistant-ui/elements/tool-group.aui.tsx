"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Wrench, CheckCircle2, AlertCircle, Clock } from "lucide-react";

export interface ToolExecutionTrace {
  toolName: string;
  provider?: string;
  arguments?: Record<string, any>;
  durationMs?: number;
  output?: any;
  status?: "success" | "failed" | "executing";
  composioLogId?: string;
}

export interface ToolGroupProps {
  traces: ToolExecutionTrace[];
}

export function ToolGroup({ traces }: ToolGroupProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!traces || traces.length === 0) return null;

  return (
    <div
      data-testid="tool-group-trace"
      className="my-2 overflow-hidden rounded-lg border border-neutral-800 bg-neutral-900/60 text-xs text-neutral-300"
    >
      {/* Header bar */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-3 py-2 text-left transition-colors hover:bg-neutral-800/50"
      >
        <div className="flex items-center gap-2">
          <Wrench className="h-3.5 w-3.5 text-blue-400" />
          <span className="font-medium">
            Executed {traces.length} tool {traces.length > 1 ? "calls" : "call"}
          </span>
          <span className="rounded bg-neutral-800 px-1.5 py-0.2 font-mono text-[10px] text-neutral-400">
            {traces.map((t) => t.toolName).join(", ")}
          </span>
        </div>

        <div className="flex items-center gap-2 text-neutral-400">
          {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </div>
      </button>

      {/* Expanded details */}
      {isOpen && (
        <div className="border-t border-neutral-800/80 p-3 space-y-3 bg-neutral-950/40 font-mono text-[11px]">
          {traces.map((trace, idx) => (
            <div key={idx} className="space-y-1.5 border-b border-neutral-800/50 pb-2.5 last:border-0 last:pb-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-semibold text-neutral-200">
                  {trace.status === "success" && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                  {trace.status === "failed" && <AlertCircle className="h-3.5 w-3.5 text-red-400" />}
                  {trace.status === "executing" && <Clock className="h-3.5 w-3.5 text-amber-400" />}
                  <span>{trace.toolName}</span>
                </div>

                <div className="flex items-center gap-2 text-neutral-400">
                  {trace.durationMs !== undefined && <span>{trace.durationMs}ms</span>}
                  {trace.composioLogId && (
                    <span
                      title="Composio Correlation Log ID"
                      className="rounded bg-indigo-950/80 px-1.5 py-0.5 text-[10px] text-indigo-300 border border-indigo-800/50"
                    >
                      {trace.composioLogId}
                    </span>
                  )}
                </div>
              </div>

              {/* Arguments */}
              {trace.arguments && Object.keys(trace.arguments).length > 0 && (
                <div>
                  <span className="text-neutral-500">args: </span>
                  <span className="text-neutral-300">{JSON.stringify(trace.arguments)}</span>
                </div>
              )}

              {/* Output */}
              {trace.output && (
                <div>
                  <span className="text-neutral-500">result: </span>
                  <span className="text-neutral-300">
                    {typeof trace.output === "object" ? JSON.stringify(trace.output) : String(trace.output)}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
