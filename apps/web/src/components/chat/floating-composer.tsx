"use client";

import React, { useState, useRef } from "react";
import { Plus, Mic, ArrowUp, ChevronDown, Sparkles } from "lucide-react";
import { ComposerPlusPopover } from "./composer-plus-popover";

interface FloatingComposerProps {
  onSendMessage: (text: string, mode: "chat" | "cowork", model: string) => void;
  onOpenConnectors: () => void;
  disabled?: boolean;
}

export function FloatingComposer({
  onSendMessage,
  onOpenConnectors,
  disabled,
}: FloatingComposerProps) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"chat" | "cowork">("chat");
  const [model, setModel] = useState<"gemini-3.8-flash" | "gemini-3.7-flash">("gemini-3.8-flash");
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim(), mode, model);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      {/* Popover anchored to Plus (+) */}
      <ComposerPlusPopover
        isOpen={showPlusMenu}
        onClose={() => setShowPlusMenu(false)}
        onOpenConnectors={onOpenConnectors}
        webSearchEnabled={webSearchEnabled}
        onToggleWebSearch={() => setWebSearchEnabled(!webSearchEnabled)}
      />

      {/* Model Selector Dropdown */}
      {showModelMenu && (
        <div className="absolute bottom-14 right-20 w-52 p-1.5 rounded-xl border border-border bg-popover shadow-xl z-50 text-xs text-foreground animate-in fade-in duration-150">
          <button
            onClick={() => {
              setModel("gemini-3.8-flash");
              setShowModelMenu(false);
            }}
            className={`w-full flex items-center justify-between p-2 rounded-lg text-left transition-colors ${
              model === "gemini-3.8-flash" ? "bg-accent font-medium" : "hover:bg-accent/60"
            }`}
          >
            <div>
              <p>Gemini 3.8 Flash</p>
              <p className="text-[10px] text-muted-foreground">Thinking reasoning • Ultra-fast</p>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">Default</span>
          </button>
          <button
            onClick={() => {
              setModel("gemini-3.7-flash");
              setShowModelMenu(false);
            }}
            className={`w-full flex items-center justify-between p-2 rounded-lg text-left transition-colors ${
              model === "gemini-3.7-flash" ? "bg-accent font-medium" : "hover:bg-accent/60"
            }`}
          >
            <div>
              <p>Gemini 3.7 Flash</p>
              <p className="text-[10px] text-muted-foreground">General tasks • High throughput</p>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">Fast</span>
          </button>
        </div>
      )}

      {/* Capsule Container */}
      <div className="w-full bg-card border border-border rounded-2xl shadow-md p-3.5 flex flex-col gap-2.5 transition-all focus-within:border-border/80 focus-within:shadow-lg">
        {/* Text Input */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="How can I help you today?"
          rows={1}
          className="w-full min-h-[44px] max-h-44 resize-none bg-transparent outline-none text-sm sm:text-base text-foreground placeholder:text-muted-foreground/80 leading-relaxed"
        />

        {/* Bottom Action Bar */}
        <div className="flex items-center justify-between pt-1">
          {/* Left Cluster */}
          <div className="flex items-center gap-2">
            {/* Plus (+) Action Button */}
            <button
              onClick={() => setShowPlusMenu(!showPlusMenu)}
              className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title="Add tools, files, or connectors"
            >
              <Plus className="h-4 w-4" />
            </button>

            {/* Segmented Mode Pill [ Chat | Cowork ] */}
            <div className="rounded-full bg-muted/60 p-0.5 flex items-center text-xs font-medium border border-border/40">
              <button
                onClick={() => setMode("chat")}
                className={`rounded-full px-2.5 py-1 transition-all ${
                  mode === "chat"
                    ? "bg-background text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Chat
              </button>
              <button
                onClick={() => setMode("cowork")}
                className={`rounded-full px-2.5 py-1 transition-all ${
                  mode === "cowork"
                    ? "bg-background text-foreground shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Cowork
              </button>
            </div>
          </div>

          {/* Right Cluster */}
          <div className="flex items-center gap-1.5">
            {/* ModelSelector Pill */}
            <button
              onClick={() => setShowModelMenu(!showModelMenu)}
              className="h-8 px-2.5 rounded-full border border-border/60 hover:bg-accent text-xs font-medium flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
              <span>{model === "gemini-3.8-flash" ? "3.8 Flash" : "3.7 Flash"}</span>
              <ChevronDown className="w-3 h-3 text-muted-foreground" />
            </button>

            {/* Microphone Button */}
            <button
              onClick={() => setIsRecording(!isRecording)}
              className={`h-8 w-8 rounded-full flex items-center justify-center transition-colors ${
                isRecording
                  ? "bg-red-500 text-white animate-pulse"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
              title="Speech-to-text dictation"
            >
              <Mic className="h-4 w-4" />
            </button>

            {/* Voice Orb / Waveform Indicator */}
            <div
              className="h-8 px-2 rounded-full hover:bg-accent flex items-center gap-0.5 cursor-pointer text-muted-foreground hover:text-foreground transition-colors"
              title="Voice mode"
            >
              <span className="w-0.5 h-3 bg-muted-foreground/60 rounded-full" />
              <span className="w-0.5 h-4 bg-muted-foreground/80 rounded-full" />
              <span className="w-0.5 h-2 bg-muted-foreground/60 rounded-full" />
              <ChevronDown className="w-2.5 h-2.5 ml-0.5" />
            </div>

            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={!text.trim() || disabled}
              className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center transition-all disabled:opacity-30 hover:opacity-90"
              title="Send message (Enter)"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
