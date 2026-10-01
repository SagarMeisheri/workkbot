"use client";

import React, { useState, useRef } from "react";
import {
  Plus,
  Mic,
  ArrowUp,
  ChevronDown,
  Sparkles,
  Wrench,
  Globe,
  Paperclip,
  X,
  FileText,
} from "lucide-react";
import { QuickToolsPopover } from "./quick-tools-popover";
import { QuickSkillsPopover } from "./quick-skills-popover";

interface FloatingComposerProps {
  onSendMessage: (text: string, model: string) => void;
  onOpenConnectors: () => void;
  disabled?: boolean;
  compact?: boolean;
  user?: any;
}

export function FloatingComposer({
  onSendMessage,
  onOpenConnectors,
  disabled,
  compact = false,
  user,
}: FloatingComposerProps) {
  const [text, setText] = useState("");
  const [model, setModel] = useState<"gemini-3.8-flash" | "gemini-3.7-flash">("gemini-3.8-flash");
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [showToolsMenu, setShowToolsMenu] = useState(false);
  const [showSkillsMenu, setShowSkillsMenu] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if ((!text.trim() && attachedFiles.length === 0) || disabled) return;
    onSendMessage(text.trim(), model);
    setText("");
    setAttachedFiles([]);
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
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        compact ? 120 : 180
      )}px`;
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setAttachedFiles((prev) => [...prev, ...newFiles]);
    }
    // Reset input value so same file can be re-selected if removed
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleRemoveFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className={`relative w-full ${compact ? "max-w-3xl" : "max-w-2xl"} mx-auto`}>
      {/* Hidden Native File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        className="hidden"
      />

      {/* Model Selector Dropdown */}
      {showModelMenu && (
        <div
          className={`absolute ${
            compact ? "bottom-12 right-2" : "top-full right-0 mt-2"
          } w-52 p-1.5 rounded-xl border border-border bg-popover shadow-xl z-50 text-xs text-foreground animate-in fade-in duration-150`}
        >
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

      {compact ? (
        /* Compact Capsule Bar (Active Chat State - Claude Style) */
        <div className="flex flex-col gap-1.5">
          {/* File Attachment Chips */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-1">
              {attachedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-accent border border-border text-xs text-foreground animate-in fade-in duration-150"
                >
                  <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="max-w-[140px] truncate">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(idx)}
                    className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="w-full bg-card border border-border/80 rounded-2xl shadow-sm px-3 py-2 flex items-center gap-2 transition-all focus-within:border-border focus-within:shadow-md relative">
            {/* Plus (+) File Upload Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="h-8 w-8 rounded-full shrink-0 flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title="Upload files"
            >
              <Plus className="h-4 w-4" />
            </button>

            {/* Quick Tools & Skills Pill Container */}
            <div className="relative flex items-center gap-1 shrink-0">
              <button
                type="button"
                onClick={() => {
                  setShowToolsMenu(!showToolsMenu);
                  setShowSkillsMenu(false);
                }}
                className={`h-7 px-2 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors ${
                  showToolsMenu
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                }`}
                title="Manage tools"
              >
                <Wrench className="w-3 h-3" />
                <span className="hidden sm:inline">Tools</span>
                <ChevronDown className="w-2.5 h-2.5" />
              </button>

              <QuickToolsPopover
                isOpen={showToolsMenu}
                onClose={() => setShowToolsMenu(false)}
                onOpenFullHub={onOpenConnectors}
                user={user}
                alignDirection="up"
              />
            </div>

            {/* Compact auto-expanding single-line text input */}
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder="Write a message..."
              rows={1}
              className="flex-1 min-h-[26px] max-h-32 resize-none bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground/70 leading-normal py-0.5"
            />

            {/* Right Action Icons */}
            <div className="flex items-center gap-1 shrink-0">
              {/* Microphone Button */}
              <button
                type="button"
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

              {/* Send Button */}
              <button
                type="button"
                onClick={handleSend}
                disabled={(!text.trim() && attachedFiles.length === 0) || disabled}
                className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center transition-all disabled:opacity-20 hover:opacity-90"
                title="Send message (Enter)"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Subdued Footer Note & Model Tag */}
          <div className="flex items-center justify-between px-2 text-[11px] text-muted-foreground/75">
            <span>Workkbot can make mistakes. Please double-check responses.</span>
            <button
              type="button"
              onClick={() => setShowModelMenu(!showModelMenu)}
              className="flex items-center gap-1 hover:text-foreground transition-colors text-[11px]"
            >
              <span>{model === "gemini-3.8-flash" ? "Gemini 3.8 Flash" : "Gemini 3.7 Flash"}</span>
              <ChevronDown className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>
      ) : (
        /* Full-sized Open Capsule (Cold Landing State) */
        <div className="w-full bg-card border border-border rounded-2xl shadow-md p-3.5 flex flex-col gap-2.5 transition-all focus-within:border-border/80 focus-within:shadow-lg relative">
          {/* File Attachment Chips */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pb-1 border-b border-border/50">
              {attachedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-accent border border-border text-xs text-foreground animate-in fade-in duration-150"
                >
                  <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="max-w-[160px] truncate">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(idx)}
                    className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

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
            {/* Left Cluster: (+) File Upload and Tabbed Pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {/* Plus (+) Button dedicated for File Upload */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                title="Add files or photos"
              >
                <Plus className="h-4 w-4" />
              </button>

              {/* Skills Pill Tab */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setShowSkillsMenu(!showSkillsMenu);
                    setShowToolsMenu(false);
                  }}
                  className={`h-8 px-2.5 rounded-full border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                    showSkillsMenu
                      ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                      : "border-border/60 hover:bg-accent text-muted-foreground hover:text-foreground"
                  }`}
                  title="Skills"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
                  <span>Skills</span>
                </button>

                <QuickSkillsPopover
                  isOpen={showSkillsMenu}
                  onClose={() => setShowSkillsMenu(false)}
                />
              </div>

              {/* Tools Pill Tab (Anchored Downward) */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setShowToolsMenu(!showToolsMenu);
                    setShowSkillsMenu(false);
                  }}
                  className={`h-8 px-2.5 rounded-full border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                    showToolsMenu
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-semibold"
                      : "border-border/60 hover:bg-accent text-muted-foreground hover:text-foreground"
                  }`}
                  title="Tools & MCP integrations"
                >
                  <Wrench className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  <span>Tools</span>
                  <ChevronDown className="w-3 h-3 text-muted-foreground" />
                </button>

                <QuickToolsPopover
                  isOpen={showToolsMenu}
                  onClose={() => setShowToolsMenu(false)}
                  onOpenFullHub={onOpenConnectors}
                  user={user}
                />
              </div>

              {/* Web Search Toggle Pill */}
              <button
                type="button"
                onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                className={`h-8 px-2.5 rounded-full border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  webSearchEnabled
                    ? "border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300"
                    : "border-border/60 hover:bg-accent text-muted-foreground/70"
                }`}
                title="Toggle Web search grounding"
              >
                <Globe className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Web Search</span>
                {/* Mini toggle indicator */}
                <span
                  className={`w-2 h-2 rounded-full transition-colors ${
                    webSearchEnabled ? "bg-blue-600 dark:bg-blue-400 animate-pulse" : "bg-muted-foreground/40"
                  }`}
                />
              </button>
            </div>

            {/* Right Cluster */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setShowModelMenu(!showModelMenu)}
                className="h-8 px-2.5 rounded-full border border-border/60 hover:bg-accent text-xs font-medium flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
                <span>{model === "gemini-3.8-flash" ? "3.8 Flash" : "3.7 Flash"}</span>
                <ChevronDown className="w-3 h-3 text-muted-foreground" />
              </button>

              <button
                type="button"
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

              <div
                className="h-8 px-2 rounded-full hover:bg-accent flex items-center gap-0.5 cursor-pointer text-muted-foreground hover:text-foreground transition-colors"
                title="Voice mode"
              >
                <span className="w-0.5 h-3 bg-muted-foreground/60 rounded-full" />
                <span className="w-0.5 h-4 bg-muted-foreground/80 rounded-full" />
                <span className="w-0.5 h-2 bg-muted-foreground/60 rounded-full" />
                <ChevronDown className="w-2.5 h-2.5 ml-0.5" />
              </div>

              <button
                type="button"
                onClick={handleSend}
                disabled={(!text.trim() && attachedFiles.length === 0) || disabled}
                className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center transition-all disabled:opacity-30 hover:opacity-90"
                title="Send message (Enter)"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
