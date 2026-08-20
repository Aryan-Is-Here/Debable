"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, SendHorizontal } from "lucide-react";

import type { ChatMessage, DebateRoom } from "@/lib/types";
import type { ChatStatus } from "@/hooks/use-debate-chat";
import { cn } from "@/lib/utils";
import { MAX_MESSAGE_LENGTH } from "@/services/chat";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FactCheckCard } from "@/components/fact-check-card";

interface ChatPanelProps {
  room: DebateRoom;
  messages: ChatMessage[];
  onSend: (content: string) => void;
  status: ChatStatus;
  /** Last refusal from the server, shown under the composer. */
  error: string | null;
  /** Development-only connection readout. */
  debug: string;
  className?: string;
}

/** What to tell the user while the socket is not usable. */
const STATUS_NOTICE: Partial<Record<ChatStatus, string>> = {
  connecting: "Connecting to chat…",
  reconnecting: "Reconnecting to chat…",
  refused: "Chat is unavailable for this debate.",
};

/** Text chat for a debate room: message list + composer, live over a WebSocket. */
export function ChatPanel({
  room,
  messages,
  onSend,
  status,
  error,
  debug,
  className,
}: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const notice = STATUS_NOTICE[status];
  const canSend = status === "connected";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  function handleSend() {
    const content = draft.trim();
    if (!content) return;
    onSend(content);
    setDraft("");
  }

  return (
    <div
      className={cn(
        "flex h-full min-h-0 flex-col rounded-lg border border-border bg-card",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <h2 className="text-sm font-medium">Debate chat</h2>
        {notice ? (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {status === "refused" ? null : <Loader2 className="size-3 animate-spin" />}
            {notice}
          </span>
        ) : null}
      </div>

      {/* Messages */}
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message) => {
          if (message.author === "system") {
            return message.factCheck ? (
              <FactCheckCard key={message.id} factCheck={message.factCheck} />
            ) : (
              <p
                key={message.id}
                className="text-center text-xs text-muted-foreground"
              >
                {message.content}
              </p>
            );
          }

          const isYou = message.author === "you";
          return (
            <div
              key={message.id}
              className={cn("flex flex-col", isYou ? "items-end" : "items-start")}
            >
              <span className="mb-0.5 text-xs text-muted-foreground">
                {isYou ? "You" : room.opponent.username}
              </span>
              <div
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                  isYou
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground",
                )}
              >
                {message.content}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="border-t border-border p-3">
        <div className="flex gap-2">
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            maxLength={MAX_MESSAGE_LENGTH}
            disabled={!canSend}
            placeholder={canSend ? "Type a message…" : "Waiting for chat…"}
            aria-label="Chat message"
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!canSend || !draft.trim()}
            aria-label="Send message"
          >
            <SendHorizontal className="size-4" />
          </Button>
        </div>

        {error ? (
          <p role="status" className="mt-2 text-xs text-destructive">
            {error}
          </p>
        ) : null}

        {/*
          Development-only connection readout. A quiet chat panel looks the same whether the
          socket is live, retrying, or dead — the equivalent ambiguity in the waiting room
          cost three rounds of debugging in Phase 4. Hidden in production builds.
        */}
        {process.env.NODE_ENV === "development" ? (
          <p className="mt-2 font-mono text-[10px] text-muted-foreground">dev · {debug}</p>
        ) : null}
      </div>
    </div>
  );
}
