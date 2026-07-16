"use client";

import { useEffect, useRef, useState } from "react";
import { SendHorizontal } from "lucide-react";

import type { ChatMessage, DebateRoom } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FactCheckCard } from "@/components/fact-check-card";

interface ChatPanelProps {
  room: DebateRoom;
  messages: ChatMessage[];
  onSend: (content: string) => void;
  className?: string;
}

/** Text chat for a debate room: message list + composer. Mock transport. */
export function ChatPanel({ room, messages, onSend, className }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

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
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-medium">Debate chat</h2>
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
      <div className="flex gap-2 border-t border-border p-3">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Type a message…"
          aria-label="Chat message"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!draft.trim()}
          aria-label="Send message"
        >
          <SendHorizontal className="size-4" />
        </Button>
      </div>
    </div>
  );
}
