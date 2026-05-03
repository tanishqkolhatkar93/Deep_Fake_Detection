"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { AnimatePresence, motion } from "framer-motion";
import {
  Command,
  FileUp,
  ImageIcon,
  LoaderIcon,
  MonitorIcon,
  Paperclip,
  SendIcon,
  Sparkles,
  XIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface UseAutoResizeTextareaProps {
  minHeight: number;
  maxHeight?: number;
}

function useAutoResizeTextarea({ minHeight, maxHeight }: UseAutoResizeTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(
    (reset?: boolean) => {
      const textarea = textareaRef.current;
      if (!textarea) {
        return;
      }

      if (reset) {
        textarea.style.height = `${minHeight}px`;
        return;
      }

      textarea.style.height = `${minHeight}px`;
      const newHeight = Math.max(
        minHeight,
        Math.min(textarea.scrollHeight, maxHeight ?? Number.POSITIVE_INFINITY),
      );

      textarea.style.height = `${newHeight}px`;
    },
    [maxHeight, minHeight],
  );

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = `${minHeight}px`;
    }
  }, [minHeight]);

  useEffect(() => {
    const handleResize = () => adjustHeight();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [adjustHeight]);

  return { textareaRef, adjustHeight };
}

interface CommandSuggestion {
  icon: React.ReactNode;
  label: string;
  description: string;
  prefix: string;
  targetId?: string;
  href?: string;
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  containerClassName?: string;
  showRing?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, containerClassName, showRing = true, ...props }, ref) => {
    const [isFocused, setIsFocused] = React.useState(false);

    return (
      <div className={cn("relative", containerClassName)}>
        <textarea
          className={cn(
            "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm transition-all duration-200 ease-in-out placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
            showRing ? "focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0" : "",
            className,
          )}
          ref={ref}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          {...props}
        />

        {showRing && isFocused ? (
          <motion.span
            className="pointer-events-none absolute inset-0 rounded-md ring-2 ring-violet-500/30 ring-offset-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
        ) : null}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";

const commandSuggestions: CommandSuggestion[] = [
  {
    icon: <ImageIcon className="h-4 w-4" />,
    label: "Scan image",
    description: "Jump to the image upload scanner",
    prefix: "/scan-image",
    targetId: "scanner",
  },
  {
    icon: <FileUp className="h-4 w-4" />,
    label: "Check video",
    description: "Jump to the video upload workflow",
    prefix: "/scan-video",
    targetId: "scanner",
  },
  {
    icon: <MonitorIcon className="h-4 w-4" />,
    label: "API docs",
    description: "Open the public inference API reference",
    prefix: "/api-docs",
    href: "https://tanishq93-deepfake-detection.hf.space/docs",
  },
  {
    icon: <Sparkles className="h-4 w-4" />,
    label: "System design",
    description: "Scroll to the deployment architecture section",
    prefix: "/system",
    targetId: "architecture",
  },
];

function performCommand(command: CommandSuggestion) {
  if (command.href) {
    window.open(command.href, "_blank", "noopener,noreferrer");
    return;
  }

  if (command.targetId) {
    document.getElementById(command.targetId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
}

export function AnimatedAIChat() {
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState<number>(-1);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [recentCommand, setRecentCommand] = useState<string | null>(null);
  const [inputFocused, setInputFocused] = useState(false);
  const [isPending, startTransition] = useTransition();
  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 60,
    maxHeight: 200,
  });
  const commandPaletteRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  const syncCommandState = useCallback((nextValue: string) => {
    if (nextValue.startsWith("/") && !nextValue.includes(" ")) {
      setShowCommandPalette(true);
      const matchingSuggestionIndex = commandSuggestions.findIndex((cmd) =>
        cmd.prefix.startsWith(nextValue),
      );
      setActiveSuggestion(matchingSuggestionIndex);
      return;
    }

    setShowCommandPalette(false);
    setActiveSuggestion(-1);
  }, []);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      setMousePosition({ x: event.clientX, y: event.clientY });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      const commandButton = document.querySelector("[data-command-button]");

      if (
        commandPaletteRef.current &&
        !commandPaletteRef.current.contains(target) &&
        !commandButton?.contains(target)
      ) {
        setShowCommandPalette(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const triggerCommand = (command: CommandSuggestion) => {
    setRecentCommand(command.label);
    performCommand(command);
    window.setTimeout(() => setRecentCommand(null), 2400);
  };

  const handleSendMessage = () => {
    if (!value.trim()) {
      return;
    }

    const selectedCommand =
      commandSuggestions.find((item) => value.trim().startsWith(item.prefix)) ?? null;

    startTransition(() => {
      setIsTyping(true);
      window.setTimeout(() => {
        setIsTyping(false);
        if (selectedCommand) {
          triggerCommand(selectedCommand);
        } else {
          document.getElementById("scanner")?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
          setRecentCommand("Scanner");
          window.setTimeout(() => setRecentCommand(null), 2400);
        }

        setValue("");
        syncCommandState("");
        adjustHeight(true);
      }, 850);
    });
  };

  const handleAttachFile = () => {
    const mockAttachments = ["frame-capture.png", "evidence-note.pdf", "story-brief.txt"];
    const nextAttachment = mockAttachments[Math.floor(Math.random() * mockAttachments.length)];
    setAttachments((current) => [...current.slice(-1), nextAttachment]);
  };

  const removeAttachment = (index: number) => {
    setAttachments((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const selectCommandSuggestion = (index: number) => {
    const selectedCommand = commandSuggestions[index];
    setValue(`${selectedCommand.prefix} `);
    setShowCommandPalette(false);
    setActiveSuggestion(-1);
    triggerCommand(selectedCommand);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showCommandPalette) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveSuggestion((previous) =>
          previous < commandSuggestions.length - 1 ? previous + 1 : 0,
        );
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveSuggestion((previous) =>
          previous > 0 ? previous - 1 : commandSuggestions.length - 1,
        );
      } else if (event.key === "Tab" || event.key === "Enter") {
        event.preventDefault();
        if (activeSuggestion >= 0) {
          selectCommandSuggestion(activeSuggestion);
        }
      } else if (event.key === "Escape") {
        event.preventDefault();
        setShowCommandPalette(false);
      }
      return;
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="relative flex min-h-[640px] w-full items-center justify-center overflow-hidden rounded-[2rem] border border-white/10 bg-[#0a1020]/70 p-4 text-white shadow-[0_30px_120px_rgba(0,0,0,0.45)] backdrop-blur-2xl sm:min-h-[720px] sm:p-6">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute left-1/4 top-0 h-96 w-96 rounded-full bg-violet-500/10 blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 h-96 w-96 rounded-full bg-cyan-500/10 blur-[128px]" />
        <div className="absolute right-1/3 top-1/4 h-64 w-64 rounded-full bg-fuchsia-500/10 blur-[96px]" />
      </div>

      {inputFocused ? (
        <motion.div
          className="pointer-events-none absolute z-0 h-[40rem] w-[40rem] rounded-full bg-gradient-to-r from-violet-500/8 via-fuchsia-500/10 to-indigo-500/10 blur-[96px]"
          animate={{
            x: mousePosition.x - 320,
            y: mousePosition.y - 320,
          }}
          transition={{
            type: "spring",
            damping: 28,
            stiffness: 140,
            mass: 0.55,
          }}
        />
      ) : null}

      <div className="relative z-10 mx-auto w-full max-w-2xl space-y-10 sm:space-y-12">
        <div className="space-y-4 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-xs uppercase tracking-[0.24em] text-white/55">
            Command-led launch flow
          </div>
          <div className="inline-block">
            <h2 className="bg-gradient-to-r from-white via-white/90 to-white/50 bg-clip-text pb-1 font-[family:var(--font-instrument-serif)] text-4xl text-transparent sm:text-5xl">
              Guide people before they second-guess the product.
            </h2>
            <motion.div
              className="h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: "100%", opacity: 1 }}
              transition={{ delay: 0.35, duration: 0.75 }}
            />
          </div>
          <p className="mx-auto max-w-xl text-sm leading-7 text-white/50">
            Inspired by premium interaction patterns from 21st.dev, but adapted to the actual
            VeriLens workflow: scanning, evidence review, API docs, and system design.
          </p>
        </div>

        <motion.div
          className="relative rounded-[1.8rem] border border-white/[0.06] bg-white/[0.03] shadow-2xl"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
        >
          <AnimatePresence>
            {showCommandPalette ? (
              <motion.div
                ref={commandPaletteRef}
                className="absolute inset-x-4 bottom-full z-50 mb-3 overflow-hidden rounded-2xl border border-white/10 bg-black/88 shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.18 }}
              >
                <div className="border-b border-white/5 px-4 py-3 text-xs uppercase tracking-[0.24em] text-white/35">
                  Suggested commands
                </div>
                <div className="py-2">
                  {commandSuggestions.map((suggestion, index) => (
                    <motion.button
                      key={suggestion.prefix}
                      type="button"
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition-colors",
                        activeSuggestion === index
                          ? "bg-white/10 text-white"
                          : "text-white/68 hover:bg-white/6 hover:text-white",
                      )}
                      onClick={() => selectCommandSuggestion(index)}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: index * 0.04 }}
                    >
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/6 text-white/70">
                        {suggestion.icon}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium">{suggestion.label}</div>
                        <div className="truncate text-xs text-white/45">{suggestion.description}</div>
                      </div>
                      <div className="text-xs text-white/35">{suggestion.prefix}</div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>

          <div className="p-5">
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(event) => {
                const nextValue = event.target.value;
                setValue(nextValue);
                syncCommandState(nextValue);
                adjustHeight();
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder="Type /scan-image, /scan-video, /api-docs, or ask to open the scanner..."
              containerClassName="w-full"
              className="min-h-[60px] w-full resize-none border-none bg-transparent px-4 py-3 text-sm text-white/90 placeholder:text-white/22 focus:outline-none"
              style={{ overflow: "hidden" }}
              showRing={false}
            />
          </div>

          <AnimatePresence>
            {attachments.length > 0 ? (
              <motion.div
                className="flex flex-wrap gap-2 px-5 pb-4"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                {attachments.map((file, index) => (
                  <motion.div
                    key={`${file}-${index}`}
                    className="flex items-center gap-2 rounded-xl bg-white/[0.04] px-3 py-2 text-xs text-white/68"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                  >
                    <span>{file}</span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(index)}
                      className="text-white/35 transition hover:text-white"
                    >
                      <XIcon className="h-3.5 w-3.5" />
                    </button>
                  </motion.div>
                ))}
              </motion.div>
            ) : null}
          </AnimatePresence>

          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.05] p-5">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleAttachFile}
                className="group relative rounded-xl p-2 text-white/45 transition hover:text-white/90"
              >
                <Paperclip className="h-4 w-4" />
                <span className="absolute inset-0 rounded-xl bg-white/[0.05] opacity-0 transition group-hover:opacity-100" />
              </button>
              <button
                type="button"
                data-command-button
                onClick={() => setShowCommandPalette((current) => !current)}
                className={cn(
                  "group relative rounded-xl p-2 text-white/45 transition hover:text-white/90",
                  showCommandPalette && "bg-white/10 text-white/95",
                )}
              >
                <Command className="h-4 w-4" />
                <span className="absolute inset-0 rounded-xl bg-white/[0.05] opacity-0 transition group-hover:opacity-100" />
              </button>
            </div>

            <button
              type="button"
              onClick={handleSendMessage}
              disabled={isTyping || isPending || !value.trim()}
              className={cn(
                "inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-medium transition-all",
                value.trim()
                  ? "bg-white text-[#07101f] shadow-[0_16px_40px_rgba(255,255,255,0.16)]"
                  : "bg-white/[0.05] text-white/35",
              )}
            >
              {isTyping || isPending ? (
                <LoaderIcon className="h-4 w-4 animate-spin" />
              ) : (
                <SendIcon className="h-4 w-4" />
              )}
              <span>Launch</span>
            </button>
          </div>
        </motion.div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          {commandSuggestions.map((suggestion, index) => (
            <motion.button
              key={suggestion.prefix}
              type="button"
              onClick={() => selectCommandSuggestion(index)}
              className="relative flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-white/65 transition hover:bg-white/[0.06] hover:text-white"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
            >
              {suggestion.icon}
              <span>{suggestion.label}</span>
            </motion.button>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {isTyping ? (
          <motion.div
            className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 shadow-lg backdrop-blur-2xl"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 18 }}
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/[0.08] text-xs font-medium text-white/90">
                VL
              </div>
              <div className="flex items-center gap-2 text-sm text-white/75">
                <span>Routing action</span>
                <TypingDots />
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {recentCommand ? (
          <motion.div
            className="absolute right-4 top-4 rounded-full border border-emerald-300/20 bg-emerald-400/10 px-4 py-2 text-[11px] uppercase tracking-[0.22em] text-emerald-100 sm:text-xs"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
          >
            Opened {recentCommand}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="ml-1 flex items-center">
      {[1, 2, 3].map((dot) => (
        <motion.div
          key={dot}
          className="mx-0.5 h-1.5 w-1.5 rounded-full bg-white/90"
          initial={{ opacity: 0.3 }}
          animate={{ opacity: [0.3, 0.95, 0.3], scale: [0.85, 1.12, 0.85] }}
          transition={{
            duration: 1.2,
            repeat: Number.POSITIVE_INFINITY,
            delay: dot * 0.14,
            ease: "easeInOut",
          }}
          style={{ boxShadow: "0 0 8px rgba(255, 255, 255, 0.25)" }}
        />
      ))}
    </div>
  );
}
