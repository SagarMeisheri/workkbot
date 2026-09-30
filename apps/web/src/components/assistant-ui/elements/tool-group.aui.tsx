"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Wrench, CheckCircle2, Clock } from "lucide-react";

export interface ToolExecutionTrace {
  toolName: string;
  provider?: string;
  arguments: Record<string, any>;
  durationMs?: number;
  output?: any;
  status?: string;
}

interface ToolGroupProps {
  traces: ToolExecutionTrace[];
}

export const ToolGroup: React.FC<ToolGroupProps> = ({ traces }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!traces || traces.length === 0) return null;

  return (
    <div
      data-testid="tool-group-trace"
      className="my-2 rounded-lg border border-zinc-800 bg-zinc-900/40 p-2 text-xs transition-colors hover:border-zinc-700"
    >
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between gap-2 text-zinc-400 hover:text-zinc-200"
      >
        <div className="flex items-center gap-2">
          <Wrench className="h-3.5 w-3.5 text-zinc-500" />
          <span className="font-mono font-medium">
            Executed {traces.length} {traces.length === 1 ? "tool" : "tools"}
          </span>
          <span className="text-[10px] text-zinc-500">
            ({traces.map((t) => t.toolName).join(", ")})
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-zinc-500">
          <CheckCircle2 className="h-3 w-3 text-emerald-500" />
          {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </div>
      </button>

      {isExpanded && (
        <div className="mt-2.5 space-y-2 border-t border-zinc-800/80 pt-2 text-zinc-300">
          {traces.map((trace, idx) => (
            <div key={idx} className="rounded border border-zinc-800/60 bg-zinc-950/60 p-2">
              <div className="flex items-center justify-between pb-1 font-mono text-[11px] text-zinc-400">
                <span className="font-semibold text-zinc-200">{trace.toolName}</span>
                {trace.durationMs !== undefined && (
                  <span className="flex items-center gap-1 text-[10px] text-zinc-500">
                    <Clock className="h-2.5 w-2.5" /> {trace.durationMs}ms
                  </span>
                )}
              </div>

              {trace.arguments && Object.keys(trace.arguments).length > 0 && (
                <div className="mt-1">
                  <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Arguments:</span>
                  <pre className="mt-0.5 overflow-x-auto rounded bg-zinc-900/60 p-1.5 font-mono text-[11px] text-zinc-300">
                    {JSON.stringify(trace.arguments, null, 2)}
                  </pre>
                </div>
              )}

              {trace.output && (
                <div className="mt-1.5">
                  <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Result:</span>
                  <pre className="mt-0.5 max-h-32 overflow-x-auto rounded bg-zinc-900/60 p-1.5 font-mono text-[11px] text-emerald-400/90">
                    {JSON.stringify(trace.output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
